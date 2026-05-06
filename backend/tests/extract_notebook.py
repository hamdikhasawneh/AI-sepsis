# --- Cell 2 ---
import sys
import numpy as np
import pandas as pd
import warnings
import joblib
from pathlib import Path
warnings.filterwarnings('ignore')

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.nn.utils.rnn import pad_sequence
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score, average_precision_score
import scipy.integrate

# Fix scipy compatibility (newer scipy removed simps)
if not hasattr(scipy.integrate, 'simps'):
    scipy.integrate.simps = scipy.integrate.simpson

from pycox.evaluation import EvalSurv

# ── Paths — adjust to your machine ─────────────────────────────
PROJECT_ROOT = Path('C:/Users/walee/AI-sepsis')
sys.path.append(str(PROJECT_ROOT / 'src'))

OUTPUT_DIR = Path("C:/Users/walee/OneDrive/Desktop/output path")
DATA_DIR   = Path("C:/Users/walee/OneDrive/Desktop/input path")

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'Device : {device}')
print(f'PyTorch: {torch.__version__}')
print('Imports OK ✓')

# --- Cell 4 ---
print('Loading data...')

cohort = pd.read_csv(OUTPUT_DIR / 'icu_cohort (1).csv')
cohort['intime']  = pd.to_datetime(cohort['intime'])
cohort['outtime'] = pd.to_datetime(cohort['outtime'])
print(f'  Cohort         : {cohort.shape}')

hourly_labels = pd.read_csv(OUTPUT_DIR / 'hourly_labels.csv')
hourly_labels['abs_time'] = pd.to_datetime(hourly_labels['abs_time'])
print(f'  Hourly labels  : {hourly_labels.shape}')

split_df = pd.read_csv(OUTPUT_DIR / 'subject_splits.csv')
print(f'  Splits         : {split_df["split"].value_counts().to_dict()}')

all_features = pd.read_csv(OUTPUT_DIR / 'engineered_features.csv')
print(f'  Features       : {all_features.shape}')

X_rich = np.load(str(OUTPUT_DIR / 'X_rich.npy'))
print(f'  X_rich         : {X_rich.shape}')

with open(OUTPUT_DIR / 'rich_feature_names.txt') as f:
    rich_feature_names = f.read().splitlines()
print(f'  Rich features  : {len(rich_feature_names)}')

stay_ids_order = pd.read_csv(
    OUTPUT_DIR / 'stay_ids_order.csv'
).squeeze().tolist()
stay_to_idx = {sid: i for i, sid in enumerate(stay_ids_order)}
print(f'  Stay order     : {len(stay_ids_order):,} stays')

with open(OUTPUT_DIR / 'feature_names.txt') as f:
    feature_names = f.read().splitlines()
feature_cols = [c for c in all_features.columns if c != 'stay_id']
print(f'  Feature cols   : {len(feature_cols)}')

print('\nAll data loaded ✓')

# --- Cell 6 ---
# ── Add hour column if missing ────────────────────────────────
if 'hour' not in hourly_labels.columns:
    cohort_times = cohort[['stay_id', 'intime']].copy()
    hourly_labels = hourly_labels.merge(cohort_times, on='stay_id', how='left')
    hourly_labels['hour'] = (
        (hourly_labels['abs_time'] - hourly_labels['intime'])
        .dt.total_seconds() / 3600
    ).astype(int)

# ── Sepsis onset per stay ─────────────────────────────────────
sepsis_onset = (
    hourly_labels[hourly_labels['label'] == 1]
    .groupby('stay_id')['hour'].min()
    .reset_index().rename(columns={'hour': 'sepsis_hour'})
)

# ── ICU stay duration ─────────────────────────────────────────
cohort_duration = cohort[['stay_id', 'intime', 'outtime']].copy()
cohort_duration['intime']  = pd.to_datetime(cohort_duration['intime'])
cohort_duration['outtime'] = pd.to_datetime(cohort_duration['outtime'])
cohort_duration['icu_hours'] = (
    (cohort_duration['outtime'] - cohort_duration['intime'])
    .dt.total_seconds() / 3600
).round(1).clip(lower=1)

# ── Full survival_df (all sepsis) ─────────────────────────────
survival_df = (
    pd.DataFrame({'stay_id': stay_ids_order})
    .merge(sepsis_onset,                              on='stay_id', how='left')
    .merge(cohort_duration[['stay_id','icu_hours']],  on='stay_id', how='left')
    .merge(cohort[['stay_id', 'subject_id']],         on='stay_id', how='left')
    .merge(split_df,                                  on='subject_id', how='left')
    .merge(all_features,                              on='stay_id', how='left')
)
survival_df['event']    = survival_df['sepsis_hour'].notna().astype(int)
survival_df['duration'] = np.where(
    survival_df['event'] == 1,
    survival_df['sepsis_hour'],
    survival_df['icu_hours']
).clip(1)
survival_df = survival_df.dropna(subset=['duration', 'split'])
survival_df['duration'] = survival_df['duration'].astype(float)
survival_df['event']    = survival_df['event'].astype(int)

# ── Incident sepsis (onset > 4h) ──────────────────────────────
EXCLUSION_WINDOW = 4
incident_sepsis  = survival_df[(survival_df['event']==1) & (survival_df['duration'] > EXCLUSION_WINDOW)]
no_sepsis        = survival_df[survival_df['event'] == 0]
survival_incident = pd.concat([incident_sepsis, no_sepsis]).reset_index(drop=True)
survival_incident['event'] = survival_incident['event'].astype(int)

print(f'survival_df (all sepsis) : {len(survival_df):,} stays, '
      f'{survival_df["event"].sum():,} events ({survival_df["event"].mean():.3%})')
print(f'survival_incident        : {len(survival_incident):,} stays, '
      f'{survival_incident["event"].sum():,} events ({survival_incident["event"].mean():.3%})')
print('Survival datasets built ✓')

# --- Cell 8 ---
# ── Discrete time grid ────────────────────────────────────────
NUM_BINS  = 48
MAX_HOURS = 200
BATCH_SIZE = 512

time_cuts = np.linspace(0, MAX_HOURS, NUM_BINS + 1)[1:]
print(f'NUM_BINS={NUM_BINS}, MAX_HOURS={MAX_HOURS}h, '
      f'bin_width={MAX_HOURS/NUM_BINS:.1f}h')

# ── Train / val / test splits ─────────────────────────────────
train_inc = survival_incident[survival_incident['split'] == 'train']
val_inc   = survival_incident[survival_incident['split'] == 'val']
test_inc  = survival_incident[survival_incident['split'] == 'test']

train_all = survival_df[survival_df['split'] == 'train']
val_all   = survival_df[survival_df['split'] == 'val']
test_all  = survival_df[survival_df['split'] == 'test']

# ── Imputation medians for rich vitals ────────────────────────
VITAL_MEDIANS_RICH = np.array([
    65.0, 85.0, 115.0, 80.0, 18.0, 97.0, 37.0,
    1.5, 8.0, 0.0, 0.0, 0.0, 60.0, 0.0, 0.7,
    0.0, 0.0, 5.0, 200.0, 1.1, 0.0, 0.0, 0.0, 0.0, 0.0,
], dtype=np.float32)

def impute_sequence_rich(x: np.ndarray) -> np.ndarray:
    df = pd.DataFrame(x, columns=rich_feature_names)
    df = df.ffill().bfill()
    for i, col in enumerate(df.columns):
        df[col] = df[col].fillna(VITAL_MEDIANS_RICH[i])
    fresh_cols = [c for c in df.columns if c.endswith('_fresh')]
    if fresh_cols:
        fresh_idx = [rich_feature_names.index(c) for c in fresh_cols]
        df[fresh_cols] = x[:, fresh_idx]
        df[fresh_cols] = df[fresh_cols].fillna(0.0)
    return df.values.astype(np.float32)

# ── Dataset class ─────────────────────────────────────────────
class DynamicDeepHitDataset(Dataset):
    def __init__(self, survival_df, stay_to_idx,
                 X_rich, all_features, feature_cols,
                 cuts, max_hours=MAX_HOURS):
        self.samples = []
        skipped = 0
        for _, row in survival_df.iterrows():
            stay_id = row['stay_id']
            if stay_id not in stay_to_idx:
                skipped += 1
                continue
            idx      = stay_to_idx[stay_id]
            duration = min(row['duration'], max_hours)
            event    = int(row['event'])
            seq_hours = max(min(int(duration), 24), 1)
            x_seq     = impute_sequence_rich(X_rich[idx, :seq_hours, :])
            feat_row  = all_features[all_features['stay_id'] == stay_id]
            if len(feat_row) == 0:
                skipped += 1
                continue
            x_static = feat_row[feature_cols].values[0].astype(np.float32)
            x_static = np.nan_to_num(x_static, nan=0.0)
            bin_idx  = min(int(np.searchsorted(cuts, duration, side='right')), len(cuts)-1)
            self.samples.append({
                'x_seq'   : torch.tensor(x_seq,     dtype=torch.float32),
                'x_static': torch.tensor(x_static,  dtype=torch.float32),
                'bin_idx' : torch.tensor(bin_idx,   dtype=torch.long),
                'event'   : torch.tensor(event,     dtype=torch.long),
                'length'  : torch.tensor(seq_hours, dtype=torch.long),
                'duration': torch.tensor(duration,  dtype=torch.float32),
            })
        print(f'  Built {len(self.samples):,} samples ({skipped:,} skipped)')

    def __len__(self):  return len(self.samples)
    def __getitem__(self, idx): return self.samples[idx]


def collate_ddh(batch):
    x_seqs    = [s['x_seq']    for s in batch]
    x_statics = torch.stack([s['x_static'] for s in batch])
    bin_idxs  = torch.stack([s['bin_idx']  for s in batch])
    events    = torch.stack([s['event']    for s in batch])
    lengths   = torch.stack([s['length']   for s in batch])
    durations = torch.stack([s['duration'] for s in batch])
    return (pad_sequence(x_seqs, batch_first=True),
            x_statics, lengths, bin_idxs, events, durations)


# ── Build loaders ─────────────────────────────────────────────
print('Building Dataset 1 (Incident Sepsis)...')
train_loader_inc = DataLoader(DynamicDeepHitDataset(train_inc, stay_to_idx, X_rich, all_features, feature_cols, time_cuts),
                              batch_size=BATCH_SIZE, shuffle=True,  collate_fn=collate_ddh, num_workers=0)
val_loader_inc   = DataLoader(DynamicDeepHitDataset(val_inc,   stay_to_idx, X_rich, all_features, feature_cols, time_cuts),
                              batch_size=BATCH_SIZE, shuffle=False, collate_fn=collate_ddh, num_workers=0)
test_loader_inc  = DataLoader(DynamicDeepHitDataset(test_inc,  stay_to_idx, X_rich, all_features, feature_cols, time_cuts),
                              batch_size=BATCH_SIZE, shuffle=False, collate_fn=collate_ddh, num_workers=0)

print('\nBuilding Dataset 2 (All Sepsis)...')
train_loader_all = DataLoader(DynamicDeepHitDataset(train_all, stay_to_idx, X_rich, all_features, feature_cols, time_cuts),
                              batch_size=BATCH_SIZE, shuffle=True,  collate_fn=collate_ddh, num_workers=0)
val_loader_all   = DataLoader(DynamicDeepHitDataset(val_all,   stay_to_idx, X_rich, all_features, feature_cols, time_cuts),
                              batch_size=BATCH_SIZE, shuffle=False, collate_fn=collate_ddh, num_workers=0)
test_loader_all  = DataLoader(DynamicDeepHitDataset(test_all,  stay_to_idx, X_rich, all_features, feature_cols, time_cuts),
                              batch_size=BATCH_SIZE, shuffle=False, collate_fn=collate_ddh, num_workers=0)

print('\nDataLoaders ready ✓')

# --- Cell 10 ---
# ── Stable DeepHit loss ───────────────────────────────────────
def deephit_loss_stable(pmf, bin_idx, event, alpha=0.2, sigma=0.1):
    eps        = 1e-7
    batch_size = pmf.size(0)
    pmf_safe   = pmf.clamp(eps, 1 - eps)

    # NLL — only for event cases
    log_pmf  = torch.log(pmf_safe)
    nll_loss = torch.tensor(0.0, device=pmf.device)
    if event.sum() > 0:
        ev_mask  = event == 1
        ev_bins  = bin_idx[ev_mask]
        nll_loss = -log_pmf[ev_mask, ev_bins].mean()

    # Ranking loss
    cif       = torch.cumsum(pmf_safe, dim=1).clamp(0, 1)
    t_i       = bin_idx.float()
    t_j       = bin_idx.float().unsqueeze(0)
    indicator = ((t_i.unsqueeze(1) < t_j) &
                 (event.unsqueeze(1) == 1)).float()
    cif_i     = cif[torch.arange(batch_size), bin_idx]
    diff      = cif_i.unsqueeze(1) - cif_i.unsqueeze(0)
    rank_loss = (indicator * torch.exp(-diff / sigma)).sum() / (indicator.sum() + eps)

    return alpha * nll_loss + (1 - alpha) * rank_loss


# ── Predict survival S(t) ─────────────────────────────────────
def predict_survival(model, loader, device, cuts):
    model.eval()
    all_pmf, all_dur, all_event = [], [], []
    with torch.no_grad():
        for x_seq, x_static, lengths, bin_idx, event, duration in loader:
            pmf = model(x_seq.to(device), x_static.to(device),
                        lengths.to(device)).cpu().numpy()
            all_pmf.append(pmf)
            all_dur.append(duration.numpy())
            all_event.append(event.numpy())
    pmf_all   = np.concatenate(all_pmf,   axis=0)
    dur_all   = np.concatenate(all_dur,   axis=0)
    event_all = np.concatenate(all_event, axis=0)
    surv_all  = 1 - np.cumsum(pmf_all, axis=1)
    return surv_all, dur_all, event_all


# ── C-index ───────────────────────────────────────────────────
def compute_cindex(surv, durations, events, cuts):
    surv_df = pd.DataFrame(surv.T, index=cuts)
    ev = EvalSurv(surv_df, durations, events, censor_surv='km')
    return ev.concordance_td()


# ── IBS ───────────────────────────────────────────────────────
def compute_ibs(surv, durations, events, cuts):
    surv_df    = pd.DataFrame(surv.T, index=cuts)
    ev         = EvalSurv(surv_df, durations, events, censor_surv='km')
    event_times = durations[events == 1]
    t_min = np.percentile(event_times, 5)
    t_max = np.percentile(event_times, 95)
    return ev.integrated_brier_score(np.linspace(t_min, t_max, 100))


# ── Calibrate survival curves ─────────────────────────────────
def calibrate_survival(surv, calibrators, num_bins):
    surv_cal    = surv.copy()
    cal_t_indices = sorted(calibrators.keys())
    for t_idx in cal_t_indices:
        iso      = calibrators[t_idx]
        cif_raw  = (1 - surv[:, t_idx]).clip(0, 1)
        cif_cal  = iso.predict(cif_raw).clip(0, 1)
        surv_cal[:, t_idx] = 1 - cif_cal

    # Interpolate between calibrated time points
    for t in range(num_bins):
        if t not in calibrators:
            lo_t = max([k for k in cal_t_indices if k <= t], default=None)
            hi_t = min([k for k in cal_t_indices if k >= t], default=None)
            if lo_t is not None and hi_t is not None and lo_t != hi_t:
                w       = (t - lo_t) / (hi_t - lo_t)
                surv_cal[:, t] = ((1 - w) * surv_cal[:, lo_t]
                                  + w * surv_cal[:, hi_t])
            elif lo_t is not None:
                surv_cal[:, t] = surv_cal[:, lo_t]
            elif hi_t is not None:
                surv_cal[:, t] = surv_cal[:, hi_t]
    return surv_cal


# ── Horizon AUROC / AUPRC ─────────────────────────────────────
HORIZONS = [6, 12, 24]

def horizon_metrics(surv, durations, events, cuts, horizons):
    results = {}
    for H in horizons:
        bin_H  = int(np.clip(np.searchsorted(cuts, H, 'right'), 0, surv.shape[1]-1))
        y_true = ((events==1) & (durations<=H)).astype(int)
        y_score= (1 - surv[:, bin_H]).clip(0, 1)
        n_pos  = int(y_true.sum())
        if n_pos < 5 or (len(y_true)-n_pos) < 5:
            results[H] = {'auroc': float('nan'), 'auprc': float('nan'),
                          'n_pos': n_pos, 'n_total': len(y_true)}
        else:
            results[H] = {'auroc': roc_auc_score(y_true, y_score),
                          'auprc': average_precision_score(y_true, y_score),
                          'n_pos': n_pos, 'n_total': len(y_true)}
    return results


print('Helper functions defined ✓')

# --- Cell 12 ---
class TransformerSurvival(nn.Module):
    """
    SurvTRACE-style Transformer survival model.

    Architecture:
      1. Vital sequence → linear projection → positional embedding
      2. Learnable CLS token captures global sequence context
      3. Transformer encoder (Pre-LN for stability)
      4. Static feature MLP encoder
      5. Fusion → softmax PMF over NUM_BINS discrete time bins
    """
    def __init__(self,
                 vital_dim      = 25,
                 static_dim     = 96,
                 d_model        = 128,
                 nhead          = 4,
                 n_layers       = 2,
                 static_hidden  = 64,
                 fusion_hidden  = 128,
                 num_bins       = NUM_BINS,
                 dropout        = 0.2,
                 max_seq_len    = 25):
        super().__init__()
        self.d_model = d_model

        self.vital_proj = nn.Linear(vital_dim, d_model)
        self.cls_token  = nn.Parameter(torch.zeros(1, 1, d_model))
        nn.init.trunc_normal_(self.cls_token, std=0.02)
        self.pos_emb = nn.Embedding(max_seq_len + 1, d_model)

        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
            norm_first=True,   # Pre-LN for stability
        )
        self.transformer = nn.TransformerEncoder(enc_layer, n_layers)

        self.static_enc = nn.Sequential(
            nn.Linear(static_dim, static_hidden),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.fusion = nn.Sequential(
            nn.LayerNorm(d_model + static_hidden),
            nn.Linear(d_model + static_hidden, fusion_hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(fusion_hidden, num_bins),
        )

    def forward(self, x_seq, x_static, lengths):
        B, T, _ = x_seq.shape
        x   = self.vital_proj(x_seq)
        cls = self.cls_token.expand(B, -1, -1)
        x   = torch.cat([cls, x], dim=1)
        pos = torch.arange(T + 1, device=x.device).unsqueeze(0)
        x   = x + self.pos_emb(pos)

        # Padding mask — True = ignore
        mask = torch.ones(B, T + 1, dtype=torch.bool, device=x.device)
        mask[:, 0] = False
        for i, l in enumerate(lengths):
            mask[i, 1:l + 1] = False

        out        = self.transformer(x, src_key_padding_mask=mask)
        cls_out    = out[:, 0, :]
        static_out = self.static_enc(x_static)
        fused      = torch.cat([cls_out, static_out], dim=1)
        return torch.softmax(self.fusion(fused), dim=1)


n_params = sum(p.numel() for p in
               TransformerSurvival(static_dim=len(feature_cols)).parameters())
print(f'TransformerSurvival parameters : {n_params:,}')
print('Architecture defined ✓')

# --- Cell 14 ---
print('=' * 55)
print('Training Transformer — Dataset 1: Incident Sepsis')
print('=' * 55)

tsurv_i = TransformerSurvival(
    vital_dim    = len(rich_feature_names),
    static_dim   = len(feature_cols),
    d_model      = 128, nhead=4, n_layers=2,
    static_hidden= 64, fusion_hidden=128,
    num_bins     = NUM_BINS, dropout=0.2,
).to(device)

optimizer_ti = torch.optim.Adam(tsurv_i.parameters(), lr=1e-4, weight_decay=1e-5)
scheduler_ti = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer_ti, mode='min', factor=0.5, patience=5)

EPOCHS   = 50
best_val = np.inf; best_ep = 0; pc = 0; patience = 10
history_ti = []

print(f"\n{'Epoch':>5} | {'Train Loss':>10} | {'Val Loss':>9} | {'LR':>8}")
print('-' * 40)

for epoch in range(1, EPOCHS + 1):
    # ── Train ────────────────────────────────────────────────
    tsurv_i.train()
    tot = 0; cnt = 0
    for xseq, xst, lens, bi, ev, dur in train_loader_inc:
        xseq, xst, lens = xseq.to(device), xst.to(device), lens.to(device)
        bi, ev = bi.to(device), ev.to(device)
        optimizer_ti.zero_grad()
        pmf  = tsurv_i(xseq, xst, lens)
        loss = deephit_loss_stable(pmf, bi, ev)
        if torch.isnan(loss): continue
        loss.backward()
        nn.utils.clip_grad_norm_(tsurv_i.parameters(), 0.5)
        optimizer_ti.step()
        tot += loss.item() * len(ev); cnt += len(ev)
    tl = tot / max(cnt, 1)

    # ── Val ──────────────────────────────────────────────────
    tsurv_i.eval()
    tot = 0; cnt = 0
    with torch.no_grad():
        for xseq, xst, lens, bi, ev, dur in val_loader_inc:
            xseq, xst, lens = xseq.to(device), xst.to(device), lens.to(device)
            bi, ev = bi.to(device), ev.to(device)
            pmf  = tsurv_i(xseq, xst, lens)
            loss = deephit_loss_stable(pmf, bi, ev)
            if torch.isnan(loss): continue
            tot += loss.item() * len(ev); cnt += len(ev)
    vl = tot / max(cnt, 1)

    lr_now = optimizer_ti.param_groups[0]['lr']
    history_ti.append({'epoch': epoch, 'train': tl, 'val': vl})
    print(f'{epoch:>5} | {tl:>10.4f} | {vl:>9.4f} | {lr_now:>8.6f}')
    scheduler_ti.step(vl)

    if vl < best_val:
        best_val = vl; best_ep = epoch; pc = 0
        torch.save(tsurv_i.state_dict(),
                   str(OUTPUT_DIR / 'transformer_incident_best.pt'))
    else:
        pc += 1
        if pc >= patience:
            print(f'\nEarly stopping at epoch {epoch} (best={best_ep})')
            break

print(f'\nBest val loss: {best_val:.4f} at epoch {best_ep}')

# --- Cell 16 ---
# Load best weights
tsurv_i.load_state_dict(torch.load(
    str(OUTPUT_DIR / 'transformer_incident_best.pt'),
    map_location=device, weights_only=True
))

# ── Raw evaluation ────────────────────────────────────────────
surv_ti, dur_ti, evt_ti = predict_survival(tsurv_i, test_loader_inc, device, time_cuts)
cindex_t_i = compute_cindex(surv_ti, dur_ti, evt_ti, time_cuts)
ibs_t_i    = compute_ibs(surv_ti, dur_ti, evt_ti, time_cuts)
print(f'Transformer Incident RAW — C-index: {cindex_t_i:.4f}  IBS: {ibs_t_i:.4f}')

# ── Calibration on val set ────────────────────────────────────
surv_tv_i, dur_tv_i, evt_tv_i = predict_survival(tsurv_i, val_loader_inc, device, time_cuts)
cals_ti = {}
for t_idx in np.arange(0, NUM_BINS, 4):
    true_label = ((evt_tv_i==1) & (dur_tv_i<=time_cuts[t_idx])).astype(float)
    pred_cif   = (1 - surv_tv_i[:, t_idx]).clip(0, 1)
    if true_label.sum() > 0 and (1-true_label).sum() > 0:
        iso = IsotonicRegression(out_of_bounds='clip')
        iso.fit(pred_cif, true_label)
        cals_ti[t_idx] = iso

surv_tic    = calibrate_survival(surv_ti, cals_ti, NUM_BINS)
cindex_t_ic = compute_cindex(surv_tic, dur_ti, evt_ti, time_cuts)
ibs_t_ic    = compute_ibs(surv_tic, dur_ti, evt_ti, time_cuts)
print(f'Transformer Incident CAL — C-index: {cindex_t_ic:.4f}  IBS: {ibs_t_ic:.4f}')

# ── Save ──────────────────────────────────────────────────────
joblib.dump(cals_ti, str(OUTPUT_DIR / 'transformer_incident_calibrators.pkl'))
np.save(str(OUTPUT_DIR / 'transformer_incident_surv_raw.npy'), surv_ti)
np.save(str(OUTPUT_DIR / 'transformer_incident_surv_cal.npy'), surv_tic)
np.save(str(OUTPUT_DIR / 'transformer_incident_dur.npy'),      dur_ti)
np.save(str(OUTPUT_DIR / 'transformer_incident_evt.npy'),      evt_ti)
print('\nDataset 1 saved ✓')

# --- Cell 18 ---
print('=' * 55)
print('Training Transformer — Dataset 2: All Sepsis')
print('=' * 55)

tsurv_a = TransformerSurvival(
    vital_dim    = len(rich_feature_names),
    static_dim   = len(feature_cols),
    d_model      = 128, nhead=4, n_layers=2,
    static_hidden= 64, fusion_hidden=128,
    num_bins     = NUM_BINS, dropout=0.2,
).to(device)

optimizer_ta = torch.optim.Adam(tsurv_a.parameters(), lr=1e-4, weight_decay=1e-5)
scheduler_ta = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer_ta, mode='min', factor=0.5, patience=5)

best_val = np.inf; best_ep = 0; pc = 0
history_ta = []

print(f"\n{'Epoch':>5} | {'Train Loss':>10} | {'Val Loss':>9} | {'LR':>8}")
print('-' * 40)

for epoch in range(1, EPOCHS + 1):
    tsurv_a.train()
    tot = 0; cnt = 0
    for xseq, xst, lens, bi, ev, dur in train_loader_all:
        xseq, xst, lens = xseq.to(device), xst.to(device), lens.to(device)
        bi, ev = bi.to(device), ev.to(device)
        optimizer_ta.zero_grad()
        pmf  = tsurv_a(xseq, xst, lens)
        loss = deephit_loss_stable(pmf, bi, ev)
        if torch.isnan(loss): continue
        loss.backward()
        nn.utils.clip_grad_norm_(tsurv_a.parameters(), 0.5)
        optimizer_ta.step()
        tot += loss.item() * len(ev); cnt += len(ev)
    tl = tot / max(cnt, 1)

    tsurv_a.eval()
    tot = 0; cnt = 0
    with torch.no_grad():
        for xseq, xst, lens, bi, ev, dur in val_loader_all:
            xseq, xst, lens = xseq.to(device), xst.to(device), lens.to(device)
            bi, ev = bi.to(device), ev.to(device)
            pmf  = tsurv_a(xseq, xst, lens)
            loss = deephit_loss_stable(pmf, bi, ev)
            if torch.isnan(loss): continue
            tot += loss.item() * len(ev); cnt += len(ev)
    vl = tot / max(cnt, 1)

    lr_now = optimizer_ta.param_groups[0]['lr']
    history_ta.append({'epoch': epoch, 'train': tl, 'val': vl})
    print(f'{epoch:>5} | {tl:>10.4f} | {vl:>9.4f} | {lr_now:>8.6f}')
    scheduler_ta.step(vl)

    if vl < best_val:
        best_val = vl; best_ep = epoch; pc = 0
        torch.save(tsurv_a.state_dict(),
                   str(OUTPUT_DIR / 'transformer_all_best.pt'))
    else:
        pc += 1
        if pc >= patience:
            print(f'\nEarly stopping at epoch {epoch} (best={best_ep})')
            break

print(f'\nBest val loss: {best_val:.4f} at epoch {best_ep}')

# --- Cell 20 ---
tsurv_a.load_state_dict(torch.load(
    str(OUTPUT_DIR / 'transformer_all_best.pt'),
    map_location=device, weights_only=True
))

surv_ta, dur_ta, evt_ta = predict_survival(tsurv_a, test_loader_all, device, time_cuts)
cindex_t_a = compute_cindex(surv_ta, dur_ta, evt_ta, time_cuts)
ibs_t_a    = compute_ibs(surv_ta, dur_ta, evt_ta, time_cuts)
print(f'Transformer All-Sepsis RAW — C-index: {cindex_t_a:.4f}  IBS: {ibs_t_a:.4f}')

surv_tv_a, dur_tv_a, evt_tv_a = predict_survival(tsurv_a, val_loader_all, device, time_cuts)
cals_ta = {}
for t_idx in np.arange(0, NUM_BINS, 4):
    true_label = ((evt_tv_a==1) & (dur_tv_a<=time_cuts[t_idx])).astype(float)
    pred_cif   = (1 - surv_tv_a[:, t_idx]).clip(0, 1)
    if true_label.sum() > 0 and (1-true_label).sum() > 0:
        iso = IsotonicRegression(out_of_bounds='clip')
        iso.fit(pred_cif, true_label)
        cals_ta[t_idx] = iso

surv_tac    = calibrate_survival(surv_ta, cals_ta, NUM_BINS)
cindex_t_ac = compute_cindex(surv_tac, dur_ta, evt_ta, time_cuts)
ibs_t_ac    = compute_ibs(surv_tac, dur_ta, evt_ta, time_cuts)
print(f'Transformer All-Sepsis CAL — C-index: {cindex_t_ac:.4f}  IBS: {ibs_t_ac:.4f}')

joblib.dump(cals_ta, str(OUTPUT_DIR / 'transformer_all_calibrators.pkl'))
np.save(str(OUTPUT_DIR / 'transformer_all_surv_raw.npy'), surv_ta)
np.save(str(OUTPUT_DIR / 'transformer_all_surv_cal.npy'), surv_tac)
np.save(str(OUTPUT_DIR / 'transformer_all_dur.npy'),      dur_ta)
np.save(str(OUTPUT_DIR / 'transformer_all_evt.npy'),      evt_ta)
print('\nDataset 2 saved ✓')

# --- Cell 22 ---
print('=' * 65)
print('TRANSFORMER SURVIVAL MODEL — FINAL RESULTS')
print('=' * 65)
print(f'{"Model":<35} {"C-index":>8} {"IBS":>8}')
print('-' * 55)
for label, ci, ibs in [
    ('Transformer  Incident   Raw',        cindex_t_i,  ibs_t_i),
    ('Transformer  Incident   Calibrated', cindex_t_ic, ibs_t_ic),
    ('Transformer  All Sepsis Raw',        cindex_t_a,  ibs_t_a),
    ('Transformer  All Sepsis Calibrated', cindex_t_ac, ibs_t_ac),
]:
    print(f'{label:<35} {ci:>8.4f} {ibs:>8.4f}')
print('=' * 65)

# ── Horizon metrics ───────────────────────────────────────────
print('\nAUROC / AUPRC at fixed horizons (Calibrated models):')
for tag, surv, durs, evts in [
    ('Incident',   surv_tic, dur_ti, evt_ti),
    ('All Sepsis', surv_tac, dur_ta, evt_ta),
]:
    res = horizon_metrics(surv, durs, evts, time_cuts, HORIZONS)
    print(f'  {tag}:')
    for H in HORIZONS:
        r = res[H]
        print(f'    {H:>2}h — AUROC: {r["auroc"]:.4f}  AUPRC: {r["auprc"]:.4f}  '
              f'(n_pos={r["n_pos"]}/{r["n_total"]})')

# ── File checklist ────────────────────────────────────────────
print('\nFile checklist:')
files = [
    'transformer_incident_best.pt',
    'transformer_incident_calibrators.pkl',
    'transformer_incident_surv_raw.npy',
    'transformer_incident_surv_cal.npy',
    'transformer_incident_dur.npy',
    'transformer_incident_evt.npy',
    'transformer_all_best.pt',
    'transformer_all_calibrators.pkl',
    'transformer_all_surv_raw.npy',
    'transformer_all_surv_cal.npy',
    'transformer_all_dur.npy',
    'transformer_all_evt.npy',
]
all_good = True
for fname in files:
    exists = (OUTPUT_DIR / fname).exists()
    if not exists: all_good = False
    print(f'  {"✓" if exists else "✗ MISSING":<10} {fname}')

if all_good:
    print('\nAll transformer files saved ✓')
    print('Ready for rolling window code and 04_results_and_evaluation.ipynb')
else:
    print('\n⚠ Some files missing — check upstream cells')


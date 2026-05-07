import torch
import torch.nn as nn


class DynamicSurvivalTransformer(nn.Module):
    """
    Dynamic Survival Transformer (DST v2).
    Trained on incident sepsis only (onset > 4h).
    Calibrated with Platt scaling (LogisticRegression).
    Accepts variable-length sequences via growing window from hour 1.
    Output: softmax PMF over 48 discrete time bins.
    Risk score = 1 - S(h+12) derived from survival curve.
    """
    def __init__(self,
                 vital_dim=25,
                 static_dim=127,
                 d_model=256,
                 nhead=8,
                 n_layers=3,
                 static_hidden=128,
                 fusion_hidden=256,
                 num_bins=48,
                 dropout=0.2,
                 max_seq_len=200):
        super().__init__()
        self.d_model = d_model
        self.num_bins = num_bins

        self.vital_proj = nn.Linear(vital_dim, d_model)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))
        nn.init.trunc_normal_(self.cls_token, std=0.02)
        self.pos_emb = nn.Embedding(max_seq_len + 1, d_model)

        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(enc_layer, n_layers)

        self.static_enc = nn.Sequential(
            nn.Linear(static_dim, static_hidden * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(static_hidden * 2, static_hidden),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.fusion = nn.Sequential(
            nn.LayerNorm(d_model + static_hidden),
            nn.Linear(d_model + static_hidden, fusion_hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(fusion_hidden, fusion_hidden // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(fusion_hidden // 2, num_bins),
        )

    def forward(self, x_seq, x_static, lengths):
        B, T, _ = x_seq.shape
        x = self.vital_proj(x_seq)
        cls = self.cls_token.expand(B, -1, -1)
        x = torch.cat([cls, x], dim=1)
        pos = torch.arange(T + 1, device=x.device).unsqueeze(0)
        x = x + self.pos_emb(pos)
        mask = torch.ones(B, T + 1, dtype=torch.bool, device=x.device)
        mask[:, 0] = False
        for i, l in enumerate(lengths):
            mask[i, 1:l.item() + 1] = False
        out = self.transformer(x, src_key_padding_mask=mask)
        cls_out = out[:, 0, :]
        s_out = self.static_enc(x_static)
        fused = torch.cat([cls_out, s_out], dim=1)
        return torch.softmax(self.fusion(fused), dim=1)

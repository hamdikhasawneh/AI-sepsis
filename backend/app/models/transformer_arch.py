import torch
import torch.nn as nn

class TransformerSurvival(nn.Module):
    """
    SurvTRACE-style Transformer survival model.
    Extracted from 03b_transformer_only.ipynb
    """
    def __init__(self,
                 vital_dim      = 25,
                 static_dim     = 96,
                 d_model        = 128,
                 nhead          = 4,
                 n_layers       = 2,
                 static_hidden  = 64,
                 fusion_hidden  = 128,
                 num_bins       = 48,
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
            norm_first=True,
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
            # Clip length to T
            actual_l = min(l.item(), T)
            mask[i, 1:actual_l + 1] = False

        out        = self.transformer(x, src_key_padding_mask=mask)
        cls_out    = out[:, 0, :]
        static_out = self.static_enc(x_static)
        fused      = torch.cat([cls_out, static_out], dim=1)
        return torch.softmax(self.fusion(fused), dim=1)

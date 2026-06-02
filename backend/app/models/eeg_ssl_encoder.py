"""OpenMIIR SSL Encoder Models v4.6 — MultiBranch, ResNet1D, EEGNet, TemporalCNN, Transformer."""

import torch
import torch.nn as nn
import torch.nn.functional as F


class EEGTemporalCNN(nn.Module):
    """Lightweight temporal CNN encoder for EEG epochs."""

    def __init__(self, n_channels=64, n_times=896, embedding_dim=128, dropout=0.1):
        super().__init__()
        self.temporal = nn.Sequential(
            nn.Conv1d(n_channels, 64, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm1d(64), nn.GELU(), nn.Dropout(dropout),
            nn.Conv1d(64, 128, kernel_size=5, stride=2, padding=2),
            nn.BatchNorm1d(128), nn.GELU(), nn.Dropout(dropout),
            nn.Conv1d(128, 256, kernel_size=3, stride=2, padding=1),
            nn.BatchNorm1d(256), nn.GELU(),
        )
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Sequential(
            nn.Linear(256, embedding_dim),
            nn.BatchNorm1d(embedding_dim),
            nn.GELU(),
        )

    def forward(self, x):
        h = self.temporal(x)
        h = self.pool(h).squeeze(-1)
        return self.head(h)


class EEGNetStyleEncoder(nn.Module):
    """EEGNet-inspired encoder: temporal → depthwise spatial → separable."""

    def __init__(self, n_channels=64, n_times=896, embedding_dim=128, dropout=0.1):
        super().__init__()
        # Temporal
        self.temp_conv = nn.Sequential(
            nn.Conv2d(1, 16, (1, 15), padding=(0, 7)), nn.BatchNorm2d(16), nn.GELU(),
            nn.Dropout2d(dropout),
        )
        # Depthwise spatial
        self.spatial_conv = nn.Sequential(
            nn.Conv2d(16, 32, (n_channels, 1), groups=16), nn.BatchNorm2d(32), nn.GELU(),
            nn.Dropout2d(dropout),
        )
        # Separable
        self.sep_conv = nn.Sequential(
            nn.Conv2d(32, 32, (1, 7), padding=(0, 3)), nn.BatchNorm2d(32), nn.GELU(),
            nn.AvgPool2d((1, 4)), nn.Dropout2d(dropout),
            nn.Conv2d(32, 64, (1, 5), padding=(0, 2)), nn.BatchNorm2d(64), nn.GELU(),
            nn.AvgPool2d((1, 4)), nn.Dropout2d(dropout),
        )
        self.pool = nn.AdaptiveAvgPool2d((1, 8))
        self.head = nn.Sequential(
            nn.Flatten(), nn.Linear(64 * 8, embedding_dim),
            nn.BatchNorm1d(embedding_dim), nn.GELU(),
        )

    def forward(self, x):
        x = x.unsqueeze(1)  # [B, 1, C, T]
        x = self.temp_conv(x)
        x = self.spatial_conv(x)
        x = self.sep_conv(x)
        x = self.pool(x)
        return self.head(x)


class TinyTransformerEncoder(nn.Module):
    """Lightweight transformer: patchify time, then 2-layer transformer."""

    def __init__(self, n_channels=64, n_times=896, embedding_dim=128, dropout=0.1):
        super().__init__()
        patch_size = 32
        n_patches = n_times // patch_size
        self.patch_conv = nn.Conv1d(n_channels, embedding_dim, kernel_size=patch_size, stride=patch_size)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, embedding_dim))
        self.pos_embed = nn.Parameter(torch.zeros(1, n_patches + 1, embedding_dim))
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embedding_dim, nhead=8, dim_feedforward=embedding_dim * 2,
            dropout=dropout, activation="gelu", batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.norm = nn.LayerNorm(embedding_dim)

    def forward(self, x):
        x = self.patch_conv(x)  # [B, D, P]
        x = x.transpose(1, 2)  # [B, P, D]
        cls = self.cls_token.expand(x.shape[0], -1, -1)
        x = torch.cat([cls, x], dim=1)
        x = x + self.pos_embed
        x = self.transformer(x)
        return self.norm(x[:, 0])


class ProjectionHead(nn.Module):
    """SimCLR-style projection head."""

    def __init__(self, in_dim, proj_dim=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, in_dim), nn.BatchNorm1d(in_dim), nn.GELU(),
            nn.Linear(in_dim, proj_dim),
        )

    def forward(self, x):
        return F.normalize(self.net(x), dim=1)


def get_encoder(encoder_type="temporal_cnn", n_channels=64, n_times=896, embedding_dim=128):
    if encoder_type == "eegnet":
        return EEGNetStyleEncoder(n_channels, n_times, embedding_dim)
    if encoder_type == "transformer":
        return TinyTransformerEncoder(n_channels, n_times, embedding_dim)
    if encoder_type == "resnet1d":
        return EEGResNet1D(n_channels, n_times, embedding_dim)
    if encoder_type == "multibranch":
        return MultiBranchSpectralEncoder(n_channels, n_times, embedding_dim)
    return EEGTemporalCNN(n_channels, n_times, embedding_dim)


class EEGResNet1D(nn.Module):
    """Residual Conv1D encoder with dilation schedule."""

    def __init__(self, n_channels=64, n_times=896, embedding_dim=128, dropout=0.1):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv1d(n_channels, 64, 7, stride=2, padding=3),
            nn.BatchNorm1d(64), nn.GELU(),
        )
        self.blocks = nn.ModuleList()
        in_ch = 64
        for dilation in [1, 2, 4, 8]:
            self.blocks.append(_ResBlock(in_ch, in_ch * 2, dilation, dropout))
            in_ch *= 2
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Sequential(nn.Linear(in_ch, embedding_dim), nn.BatchNorm1d(embedding_dim), nn.GELU())

    def forward(self, x):
        h = self.stem(x)
        for blk in self.blocks:
            h = blk(h)
        h = self.pool(h).squeeze(-1)
        return self.head(h)


class _ResBlock(nn.Module):
    def __init__(self, in_ch, out_ch, dilation, dropout):
        super().__init__()
        self.conv1 = nn.Conv1d(in_ch, out_ch, 3, dilation=dilation, padding=dilation)
        self.bn1 = nn.BatchNorm1d(out_ch)
        self.conv2 = nn.Conv1d(out_ch, out_ch, 3, dilation=1, padding=1)
        self.bn2 = nn.BatchNorm1d(out_ch)
        self.skip = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()
        self.drop = nn.Dropout(dropout)

    def forward(self, x):
        r = self.skip(x)
        h = F.gelu(self.bn1(self.conv1(x)))
        h = F.gelu(self.bn2(self.conv2(h)))
        return self.drop(h) + r


class MultiBranchSpectralEncoder(nn.Module):
    """Multi-branch: different kernel sizes for EEG bands (slow=alpha/theta, mid=beta, fast=gamma)."""

    def __init__(self, n_channels=64, n_times=896, embedding_dim=128, dropout=0.1):
        super().__init__()
        self.branches = nn.ModuleDict({
            "slow": nn.Sequential(
                nn.Conv1d(n_channels, 32, 31, stride=2, padding=15), nn.BatchNorm1d(32), nn.GELU(),
                nn.Conv1d(32, 64, 15, stride=2, padding=7), nn.BatchNorm1d(64), nn.GELU(),
            ),
            "mid": nn.Sequential(
                nn.Conv1d(n_channels, 32, 15, stride=2, padding=7), nn.BatchNorm1d(32), nn.GELU(),
                nn.Conv1d(32, 64, 7, stride=2, padding=3), nn.BatchNorm1d(64), nn.GELU(),
            ),
            "fast": nn.Sequential(
                nn.Conv1d(n_channels, 32, 7, stride=2, padding=3), nn.BatchNorm1d(32), nn.GELU(),
                nn.Conv1d(32, 64, 3, stride=2, padding=1), nn.BatchNorm1d(64), nn.GELU(),
            ),
        })
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fuse = nn.Sequential(
            nn.Linear(64 * 3, embedding_dim), nn.BatchNorm1d(embedding_dim), nn.GELU(),
            nn.Linear(embedding_dim, embedding_dim), nn.BatchNorm1d(embedding_dim),
        )
        self.drop = nn.Dropout(dropout)

    def forward(self, x):
        feats = []
        for branch in self.branches.values():
            f = self.pool(branch(x)).squeeze(-1)
            feats.append(f)
        h = torch.cat(feats, dim=1)
        h = self.drop(h)
        return self.fuse(h)

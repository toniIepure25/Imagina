"""EEG SSL Augmentations v4.5 — Time masking, channel dropout, noise, jitter."""

import torch


def time_mask(x, mask_ratio=0.125):
    """Mask a contiguous segment of time."""
    if x.dim() == 3:
        # [B, C, T]
        B, C, T = x.shape
        mask_len = max(1, int(T * mask_ratio))
        for i in range(B):
            start = torch.randint(0, T - mask_len, (1,)).item()
            x[i, :, start:start + mask_len] = 0
    return x


def channel_dropout(x, drop_ratio=0.1):
    """Drop random channels."""
    if x.dim() == 3:
        B, C, T = x.shape
        for i in range(B):
            n_drop = max(1, int(C * drop_ratio))
            idx = torch.randperm(C)[:n_drop]
            x[i, idx] = 0
    return x


def gaussian_noise(x, std=0.05):
    """Add Gaussian noise."""
    return x + torch.randn_like(x) * std


def amplitude_scale(x, scale_range=(0.8, 1.2)):
    """Random amplitude scaling."""
    B = x.shape[0]
    scales = torch.empty(B, 1, 1, device=x.device).uniform_(*scale_range)
    return x * scales


def temporal_jitter(x, jitter_ratio=0.05):
    """Random temporal shift by cropping and padding."""
    # Simple implementation: roll along time axis
    if x.dim() == 3:
        B, C, T = x.shape
        shift = int(T * jitter_ratio)
        if shift > 0:
            s = torch.randint(-shift, shift + 1, (B,)).tolist()
            for i in range(B):
                if s[i] != 0:
                    x[i] = torch.roll(x[i], s[i], dims=-1)
    return x


def frequency_mask(x, mask_ratio=0.1):
    """Simple frequency-domain masking via low-pass filter variation."""
    if x.dim() == 3:
        return x + torch.randn_like(x) * 0.02  # Soft alternative
    return x


def make_ssl_views(batch, config=None):
    """Create two augmented views for contrastive learning."""
    if config is None:
        config = {}

    v1 = batch.clone()
    v2 = batch.clone()

    v1 = gaussian_noise(v1, config.get("noise_std", 0.05))
    v2 = gaussian_noise(v2, config.get("noise_std", 0.05))

    v1 = time_mask(v1, config.get("time_mask_ratio", 0.125))
    v2 = time_mask(v2, config.get("time_mask_ratio", 0.125))

    v1 = channel_dropout(v1, config.get("ch_drop_ratio", 0.1))
    v2 = channel_dropout(v2, config.get("ch_drop_ratio", 0.1))

    v1 = amplitude_scale(v1)
    v2 = amplitude_scale(v2)

    v1 = temporal_jitter(v1)
    v2 = temporal_jitter(v2)

    return v1, v2

"""Daily adaptations; keep published 6-hour TFT/Informer source unchanged."""
import torch
from torch import nn
from torch.nn import functional as F

from src.tft_regional import RegionalTFT, VariableSelection
from src.informer_regional_pilot import RegionalInformer


class DailyTFT(RegionalTFT):
    def __init__(self, input_features, hidden=32, heads=4, dropout=.1, history_steps=7):
        super().__init__(input_features, hidden, heads, dropout)
        self.history_steps = history_steps
        self.config.update(history_steps=history_steps)
        self.future_selection = VariableSelection(2, hidden, dropout)
        self.amount = nn.Linear(hidden, 1); self.events = nn.Linear(hidden, 3)

    def forward(self, past, calendar):
        if past.shape[1] != self.history_steps or calendar.shape[1:] != (3, 2):
            raise ValueError('Expected seven daily past steps and three two-variable future calendars')
        p, _ = self.past_selection(past); c, _ = self.future_selection(calendar)
        encoded, state = self.encoder(p); decoded, _ = self.decoder(c, state)
        selected = torch.cat([p, c], 1)
        recurrent = self.post_lstm(torch.cat([encoded, decoded], 1), selected)
        enriched = self.enrichment(recurrent)
        attended, _ = self.attention(enriched, self.history_steps)
        combined = self.post_attention(attended, enriched[:, self.history_steps:])
        days = self.final(self.positionwise(combined), recurrent[:, self.history_steps:])
        return F.softplus(self.amount(days).squeeze(-1)) + 1e-4, self.events(days)


class DailyInformer(RegionalInformer):
    def __init__(self, input_features, time_indices, hidden=32, heads=4, factor=3,
                 dropout=.1, label_len=3, history_steps=7):
        super().__init__(input_features, time_indices, hidden, heads, factor, dropout, label_len)
        if len(time_indices) != 2 or not 1 <= label_len <= history_steps:
            raise ValueError('Expected two annual calendar variables and a valid decoder prefix')
        self.history_steps = history_steps; self.config.update(history_steps=history_steps)
        self.time_center = torch.zeros(2); self.time_scale = torch.ones(2)
        self.enc_embedding.temporal_embedding.embed = nn.Linear(2, hidden)
        self.dec_embedding.temporal_embedding.embed = nn.Linear(2, hidden)
        self.amount = nn.Linear(hidden, 1); self.events = nn.Linear(hidden, 3)

    def forward(self, past, calendar):
        if past.shape[1] != self.history_steps or calendar.shape[1:] != (3, 2):
            raise ValueError('Expected seven daily past steps and three two-variable future calendars')
        past_marks = past[:, :, self.time_indices]
        future_marks = (calendar - self.time_center) / self.time_scale
        dec_values = torch.cat([past[:, -self.label_len:], past.new_zeros(len(past), 3, past.shape[-1])], 1)
        dec_marks = torch.cat([past_marks[:, -self.label_len:], future_marks], 1)
        encoded, _ = self.encoder(self.enc_embedding(past, past_marks))
        latent, _, _ = self.decoder(self.dec_embedding(dec_values, dec_marks), encoded)
        days = latent[:, -3:]
        return F.softplus(self.amount(days).squeeze(-1)) + 1e-4, self.events(days)

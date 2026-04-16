import torch
import torch.nn as nn


class GemmaForFakeNewsClassification(nn.Module):
    def __init__(self, base_model, hidden_size=1152, num_classes=2):
        super().__init__()
        self.base_model = base_model
        self.classifier = nn.Linear(hidden_size, num_classes)

    def forward(self, input_ids, attention_mask):
        outputs = self.base_model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        last_hidden_state = outputs.last_hidden_state
        last_token = last_hidden_state[:, -1, :]

        logits = self.classifier(last_token)
        return logits
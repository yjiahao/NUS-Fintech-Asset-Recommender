import torch
import torch.nn as nn

class NeuMF(nn.Module):
    """
    NeuMF: Neural Matrix Factorization combining GMF and MLP branches.
    Inputs:
      - u: LongTensor of user indices
      - i: LongTensor of item indices
    Returns:
      - Sigmoid score in [0, 1] for user-item affinity.
    """
    def __init__(self, n_users, n_items, eg=32, em=32, layers=(128, 64, 32)):
        super().__init__()
        # GMF branch (element-wise interaction)
        self.user_gmf = nn.Embedding(n_users, eg)
        self.item_gmf = nn.Embedding(n_items, eg)
        # MLP branch (learns nonlinear interaction)
        self.user_mlp = nn.Embedding(n_users, em)
        self.item_mlp = nn.Embedding(n_items, em)
        dim = em * 2
        mlp = []
        for hidden_dim in layers:
            mlp += [nn.Linear(dim, hidden_dim), nn.ReLU()]
            dim = hidden_dim
        self.mlp = nn.Sequential(*mlp)
        # Fusion layer combines GMF and MLP outputs
        self.out = nn.Linear(eg + layers[-1], 1)
        self.sig = nn.Sigmoid()
        self._init()

    def _init(self):
        for emb in [self.user_gmf, self.item_gmf, self.user_mlp, self.item_mlp]:
            nn.init.normal_(emb.weight, std=0.01)
        for module in self.mlp:
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)
        nn.init.xavier_uniform_(self.out.weight)
        nn.init.zeros_(self.out.bias)

    def forward(self, u, i):
        gmf_vec = self.user_gmf(u) * self.item_gmf(i)
        mlp_input = torch.cat([self.user_mlp(u), self.item_mlp(i)], dim=-1)
        mlp_vec = self.mlp(mlp_input)
        out = self.out(torch.cat([gmf_vec, mlp_vec], dim=-1))
        return self.sig(out.squeeze(-1))



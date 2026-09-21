"""Train ResNet-18 on clean CIFAR-10 and evaluate deterministic CIFAR-10-C files."""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", required=True)
    p.add_argument("--cifar10c-root", required=True)
    p.add_argument("--seed", type=int, default=2021)
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--batch-size", type=int, default=128)
    args = p.parse_args()

    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset
    from torchvision import datasets, models, transforms

    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_tf = transforms.Compose([
        transforms.RandomCrop(32, padding=4), transforms.RandomHorizontalFlip(),
        transforms.ToTensor(), transforms.Normalize((0.4914,0.4822,0.4465),(0.2470,0.2435,0.2616)),
    ])
    test_tf = transforms.Compose([
        transforms.ToTensor(), transforms.Normalize((0.4914,0.4822,0.4465),(0.2470,0.2435,0.2616)),
    ])
    train_ds = datasets.CIFAR10(args.data_root, train=True, download=False, transform=train_tf)
    test_ds = datasets.CIFAR10(args.data_root, train=False, download=False, transform=test_tf)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=2)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=2)

    model = models.resnet18(weights=None, num_classes=10)
    model.conv1 = nn.Conv2d(3,64,kernel_size=3,stride=1,padding=1,bias=False)
    model.maxpool = nn.Identity()
    model.to(device)
    opt = torch.optim.SGD(model.parameters(), lr=0.1, momentum=0.9, weight_decay=5e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(args.epochs,1))
    loss_fn = nn.CrossEntropyLoss()
    for _ in range(args.epochs):
        model.train()
        for x,y in train_loader:
            x,y=x.to(device),y.to(device); opt.zero_grad(set_to_none=True)
            loss=loss_fn(model(x),y); loss.backward(); opt.step()
        sched.step()

    @torch.no_grad()
    def accuracy(loader):
        model.eval(); correct=total=0
        for x,y in loader:
            pred=model(x.to(device)).argmax(1).cpu(); correct += int((pred==y).sum()); total += y.numel()
        return correct/total

    clean_acc = accuracy(test_loader)
    croot = Path(args.cifar10c_root)
    labels = np.load(croot/"labels.npy")
    corruption_scores = {}

    class ArrayDataset(Dataset):
        def __init__(self, arr, labels): self.arr=arr; self.labels=labels
        def __len__(self): return len(self.labels)
        def __getitem__(self, i):
            from PIL import Image
            return test_tf(Image.fromarray(self.arr[i])), int(self.labels[i])

    for path in sorted(croot.glob("*.npy")):
        if path.name == "labels.npy": continue
        arr = np.load(path, mmap_mode="r")
        score = accuracy(DataLoader(ArrayDataset(arr, labels), batch_size=args.batch_size, shuffle=False, num_workers=2))
        corruption_scores[path.stem] = score

    metrics = {
        "clean_accuracy": clean_acc,
        "corruption_accuracy": float(np.mean(list(corruption_scores.values()))),
        "worst_corruption_accuracy": float(min(corruption_scores.values())),
        "params": int(sum(p.numel() for p in model.parameters())),
        "corruptions": corruption_scores,
    }
    Path("metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__": main()

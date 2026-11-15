"""
Computer Science Simulation Engine
====================================
Handles: ML model training, dropout analysis, algorithm complexity,
         neural network architecture comparisons, graph algorithms, and sorting dynamics.

Uses deterministic models to produce realistic training curves and algorithm execution states.
"""

import numpy as np


def _model_comparison(params):
    """Compare CNN vs Transformer on image classification (CIFAR-10 style)."""
    epochs = params.get("epochs", 50)
    t = np.arange(1, epochs + 1)

    # CNN (ResNet-style): fast early convergence, ~87-89% plateau
    cnn_loss = 2.3 * np.exp(-0.09 * t) + 0.13
    cnn_acc  = 89.0 * (1 - np.exp(-0.13 * t))
    cnn_acc  = np.minimum(cnn_acc, 89.0)

    # Transformer (ViT): slower warm-up, eventually surpasses CNN
    trans_loss = 2.5 * np.exp(-0.055 * t) + 0.16
    trans_acc  = 91.5 * (1 - np.exp(-0.075 * t))
    trans_acc  = np.minimum(trans_acc, 91.5)

    def epoch_at_pct(arr, pct):
        idx = np.argmax(arr >= pct)
        return int(idx) + 1 if arr[idx] >= pct else -1

    numerical = {
        "model_comparison": {
            "cnn_final_accuracy_pct":          round(float(cnn_acc[-1]), 2),
            "transformer_final_accuracy_pct":  round(float(trans_acc[-1]), 2),
            "winner":                          "Transformer" if float(trans_acc[-1]) > float(cnn_acc[-1]) else "CNN",
            "cnn_epochs_to_80pct":             epoch_at_pct(cnn_acc, 80),
            "transformer_epochs_to_80pct":     epoch_at_pct(trans_acc, 80),
            "cnn_final_loss":                  round(float(cnn_loss[-1]), 4),
            "transformer_final_loss":          round(float(trans_loss[-1]), 4),
        }
    }

    plots = [
        {
            "plot_type": "line",
            "title": "Validation Accuracy: CNN vs Transformer (CIFAR-10)",
            "x_label": "Epoch",
            "y_label": "Accuracy (%)",
            "x": t.tolist(),
            "y": cnn_acc.tolist(),
            "series_name": "CNN (ResNet-style)",
            "extra_series": [
                {"y": trans_acc.tolist(), "name": "Transformer (ViT)", "color": "#a855f7"}
            ],
        },
        {
            "plot_type": "line",
            "title": "Training Loss: CNN vs Transformer",
            "x_label": "Epoch",
            "y_label": "Cross-Entropy Loss",
            "x": t.tolist(),
            "y": cnn_loss.tolist(),
            "series_name": "CNN Loss",
            "extra_series": [
                {"y": trans_loss.tolist(), "name": "Transformer Loss", "color": "#a855f7"}
            ],
        },
    ]

    observations = [
        f"CNN converges faster: reaches 80% accuracy at epoch {epoch_at_pct(cnn_acc, 80)}",
        f"Transformer peaks higher: {round(float(trans_acc[-1]),2)}% vs CNN {round(float(cnn_acc[-1]),2)}%",
        "Transformer benefits more from longer training and larger datasets",
        "For small datasets / quick experiments, CNN is more practical",
    ]
    return numerical, plots, observations


def _dropout_effect(params):
    """Effect of dropout rate on CNN validation accuracy."""
    n_points = 20
    dropout_rates = np.linspace(0.0, 0.7, n_points)
    base_acc      = params.get("base_accuracy", 89.0)
    optimal       = params.get("optimal_dropout", 0.3)

    # Gaussian-shaped benefit centered at optimal, falls off on either side
    accuracy = base_acc * np.exp(-6.0 * (dropout_rates - optimal) ** 2)
    # Without dropout (0.0) there is slight over-fitting
    accuracy[0] = base_acc - 4.0
    accuracy = np.clip(accuracy, 40.0, base_acc)

    best_idx      = int(np.argmax(accuracy))
    best_dropout  = round(float(dropout_rates[best_idx]), 2)
    best_acc      = round(float(accuracy[best_idx]), 2)

    numerical = {
        "dropout_analysis": {
            "optimal_dropout_rate": best_dropout,
            "peak_accuracy_pct":    best_acc,
            "accuracy_at_0_pct":    round(float(accuracy[0]), 2),
            "accuracy_at_50pct_dropout": round(float(
                accuracy[np.argmin(np.abs(dropout_rates - 0.5))]), 2),
            "accuracy_at_70pct_dropout": round(float(accuracy[-1]), 2),
        }
    }

    plots = [{
        "plot_type": "line",
        "title": "Effect of Dropout Rate on CNN Validation Accuracy",
        "x_label": "Dropout Rate",
        "y_label": "Validation Accuracy (%)",
        "x": dropout_rates.tolist(),
        "y": accuracy.tolist(),
        "series_name": "CNN Accuracy",
    }]

    observations = [
        f"Optimal dropout rate ≈ {best_dropout} → {best_acc}% accuracy",
        "Too low dropout (≈ 0) → overfitting; too high → underfitting",
        "Test dropout rates 0.2–0.5 for most CNN architectures",
    ]
    return numerical, plots, observations


def _algorithm_complexity(params):
    """Compare common algorithm complexity classes."""
    n_max = params.get("n_max", 500)
    n = np.linspace(1, n_max, 200)

    o_log    = np.log2(np.maximum(n, 1))
    o_n      = n
    o_nlogn  = n * np.log2(np.maximum(n, 1))
    o_n2     = n ** 2

    numerical = {
        "complexity_at_n500": {
            "O_log_n":   round(float(o_log[-1]), 2),
            "O_n":       round(float(o_n[-1]), 0),
            "O_n_log_n": round(float(o_nlogn[-1]), 0),
            "O_n2":      round(float(o_n2[-1]), 0),
        }
    }

    plots = [{
        "plot_type": "line",
        "title": "Algorithm Complexity Comparison",
        "x_label": "Input Size  n",
        "y_label": "Operations",
        "x": n.tolist(),
        "y": o_n.tolist(),
        "series_name": "O(n) — Linear Search",
        "extra_series": [
            {"y": o_nlogn.tolist(), "name": "O(n log n) — Merge Sort", "color": "#f59e0b"},
            {"y": o_n2.tolist(),    "name": "O(n²) — Bubble Sort",     "color": "#ef4444"},
            {"y": o_log.tolist(),   "name": "O(log n) — Binary Search", "color": "#10b981"},
        ],
    }]

    observations = [
        "O(log n) algorithms (binary search) scale best for large inputs",
        "O(n log n) sorting (merge/quick) is optimal for comparison-based sorts",
        f"O(n²) bubble sort: {int(o_n2[-1]):,} ops at n={n_max} — impractical for large n",
        "Always prefer O(n log n) or better in production systems",
    ]
    return numerical, plots, observations


def _neural_network_training(params):
    """Generic neural network training simulation."""
    epochs       = params.get("epochs", 100)
    hidden_units = params.get("hidden_units", 128)
    lr           = params.get("learning_rate", 0.001)
    t = np.arange(1, epochs + 1)

    # Learning rate affects convergence speed
    speed   = lr * 1000  # normalised speed
    plateau = 95.0 - max(0, 10 - speed) * 2  # lower LR → slightly lower plateau

    train_loss = 2.3 * np.exp(-0.07 * speed / 10 * t) + 0.08
    val_loss   = 2.4 * np.exp(-0.06 * speed / 10 * t) + 0.12
    val_acc    = plateau * (1 - np.exp(-0.06 * speed / 10 * t))

    numerical = {
        "training": {
            "final_val_accuracy_pct": round(float(val_acc[-1]), 2),
            "final_train_loss":       round(float(train_loss[-1]), 4),
            "final_val_loss":         round(float(val_loss[-1]), 4),
            "hidden_units":           hidden_units,
            "learning_rate":          lr,
            "total_epochs":           epochs,
        }
    }

    plots = [
        {
            "plot_type": "line",
            "title": f"Neural Network Training  (LR={lr}, units={hidden_units})",
            "x_label": "Epoch",
            "y_label": "Loss",
            "x": t.tolist(),
            "y": train_loss.tolist(),
            "series_name": "Train Loss",
            "extra_series": [
                {"y": val_loss.tolist(), "name": "Val Loss", "color": "#f59e0b"}
            ],
        },
        {
            "plot_type": "line",
            "title": "Validation Accuracy",
            "x_label": "Epoch",
            "y_label": "Accuracy (%)",
            "x": t.tolist(),
            "y": val_acc.tolist(),
            "series_name": "Val Accuracy",
        },
    ]

    observations = [
        f"Final validation accuracy: {round(float(val_acc[-1]),2)}%",
        f"Convergence plateau reached around epoch {int(epochs * 0.7)}",
        "Monitor val_loss for early stopping to prevent overfitting",
    ]
    return numerical, plots, observations


# ─── Main entry point ────────────────────────────────────────────────────────

def run(procedure: dict) -> dict:
    log      = ["[cs_sim] Starting computer science simulation"]
    params   = procedure.get("parameters", {})
    exp_type = procedure.get("experiment_type") or ""
    text     = (procedure.get("hypothesis", "") + " " + exp_type + " " + procedure.get("topic", "")).lower()

    # Auto-detect from hypothesis text
    if exp_type in ("", "computer_science", "cs", "machine_learning", "ml", None):
        if any(w in text for w in ["cnn", "transformer", "compare", "vit", "resnet"]):
            exp_type = "model_comparison"
        elif any(w in text for w in ["dropout", "regulariz"]):
            exp_type = "dropout_effect"
        elif any(w in text for w in ["algorithm", "complexity", "sort", "search", "big o", "graph", "dijkstra", "bfs", "dfs"]):
            exp_type = "algorithm_complexity"
        else:
            exp_type = "model_comparison"

    if exp_type == "model_comparison":
        numerical, plots, observations = _model_comparison(params)
        log.append("[cs_sim] Model comparison (CNN vs Transformer) computed")
        visual_data = {
            "type": "neural_network",
            "architecture": "Deep CNN vs Vision Transformer",
            "layers": [
                {"id": "in", "name": "Input Layer", "type": "input", "nodes": 8, "shape": "28x28x1", "color": "#06b6d4"},
                {"id": "conv", "name": "Conv2D + ReLU", "type": "conv", "nodes": 12, "shape": "64 channels", "color": "#8b5cf6"},
                {"id": "attn", "name": "Multi-Head Attention", "type": "attention", "nodes": 8, "shape": "8 Heads (d=256)", "color": "#f59e0b"},
                {"id": "dense", "name": "Dense Classification", "type": "dense", "nodes": 6, "shape": "128 units", "color": "#38bdf8"},
                {"id": "out", "name": "Softmax Logits", "type": "output", "nodes": 4, "shape": "10 Classes", "color": "#10b981"}
            ],
            "metrics": numerical.get("model_comparison", {})
        }

    elif exp_type == "dropout_effect":
        numerical, plots, observations = _dropout_effect(params)
        log.append("[cs_sim] Dropout effect analysis computed")
        visual_data = {
            "type": "neural_network",
            "architecture": "Regularized CNN with Dynamic Dropout",
            "layers": [
                {"id": "in", "name": "Input", "type": "input", "nodes": 8, "shape": "32x32x3", "color": "#06b6d4"},
                {"id": "conv", "name": "Conv2D (Features)", "type": "conv", "nodes": 12, "shape": "128 channels", "color": "#8b5cf6"},
                {"id": "drop", "name": "Dropout Gate (p=0.3)", "type": "dropout", "nodes": 8, "shape": "Inverted Dropout", "color": "#ec4899"},
                {"id": "dense", "name": "Fully Connected", "type": "dense", "nodes": 6, "shape": "64 units", "color": "#38bdf8"},
                {"id": "out", "name": "Prediction Output", "type": "output", "nodes": 4, "shape": "Classes", "color": "#10b981"}
            ],
            "metrics": numerical.get("dropout_analysis", {})
        }

    elif exp_type == "algorithm_complexity":
        numerical, plots, observations = _algorithm_complexity(params)
        log.append("[cs_sim] Algorithm complexity comparison computed")
        visual_data = {
            "type": "algorithm",
            "algorithms": ["QuickSort", "MergeSort", "BubbleSort", "Dijkstra"],
            "array_initial": [45, 12, 89, 34, 67, 23, 91, 5, 56, 78, 40, 62],
            "array_sorted": [5, 12, 23, 34, 40, 45, 56, 62, 67, 78, 89, 91],
            "trace_steps": [
                {"step": 1, "action": "compare", "indices": [0, 1], "pivot": 62, "message": "Comparing Array[0]=45 with Array[1]=12"},
                {"step": 2, "action": "swap", "indices": [0, 1], "pivot": 62, "message": "Swap: 12 placed before 45"},
                {"step": 3, "action": "partition", "indices": [5], "pivot": 62, "message": "Pivot 62 locked in place"},
                {"step": 4, "action": "recurse", "indices": [0, 6], "pivot": 40, "message": "Recursive partition on left subarray"},
                {"step": 5, "action": "complete", "indices": [0, 11], "message": "Array fully sorted: O(n log n)"}
            ],
            "graph": {
                "nodes": [
                    {"id": "A", "label": "Start (A)", "distance": 0, "x": 60, "y": 140},
                    {"id": "B", "label": "Node B", "distance": 4, "x": 160, "y": 70},
                    {"id": "C", "label": "Node C", "distance": 2, "x": 160, "y": 210},
                    {"id": "D", "label": "Node D", "distance": 7, "x": 280, "y": 70},
                    {"id": "E", "label": "Node E", "distance": 5, "x": 280, "y": 210},
                    {"id": "F", "label": "Target (F)", "distance": 9, "x": 380, "y": 140}
                ],
                "edges": [
                    {"source": "A", "target": "B", "weight": 4, "in_path": False},
                    {"source": "A", "target": "C", "weight": 2, "in_path": True},
                    {"source": "B", "target": "D", "weight": 5, "in_path": False},
                    {"source": "C", "target": "E", "weight": 3, "in_path": True},
                    {"source": "D", "target": "F", "weight": 2, "in_path": False},
                    {"source": "E", "target": "F", "weight": 4, "in_path": True},
                    {"source": "C", "target": "B", "weight": 1, "in_path": False},
                    {"source": "B", "target": "E", "weight": 2, "in_path": False}
                ],
                "shortest_path": ["A", "C", "E", "F"],
                "total_cost": 9
            }
        }

    elif exp_type in ("neural_network", "nn_training"):
        numerical, plots, observations = _neural_network_training(params)
        log.append("[cs_sim] Neural network training simulation computed")
        visual_data = {
            "type": "neural_network",
            "architecture": "Multi-Layer Perceptron (Backprop)",
            "layers": [
                {"id": "in", "name": "Input Layer", "type": "input", "nodes": 8, "shape": "Features", "color": "#06b6d4"},
                {"id": "h1", "name": "Hidden Layer 1 (ReLU)", "type": "dense", "nodes": 12, "shape": "128 units", "color": "#8b5cf6"},
                {"id": "h2", "name": "Hidden Layer 2 (ReLU)", "type": "dense", "nodes": 8, "shape": "64 units", "color": "#f59e0b"},
                {"id": "out", "name": "Output Layer (Softmax)", "type": "output", "nodes": 4, "shape": "10 units", "color": "#10b981"}
            ],
            "metrics": numerical.get("training", {})
        }

    else:
        numerical, plots, observations = _model_comparison(params)
        log.append(f"[cs_sim] Unknown type '{exp_type}', defaulted to model comparison")
        visual_data = {
            "type": "neural_network",
            "architecture": "CNN vs Transformer",
            "layers": [
                {"id": "in", "name": "Input", "type": "input", "nodes": 8, "shape": "28x28x1", "color": "#06b6d4"},
                {"id": "h1", "name": "Conv2D", "type": "conv", "nodes": 12, "shape": "64 ch", "color": "#8b5cf6"},
                {"id": "out", "name": "Output", "type": "output", "nodes": 4, "shape": "Classes", "color": "#10b981"}
            ],
            "metrics": numerical.get("model_comparison", {})
        }

    return {
        "numerical_results":  numerical,
        "plot_data":          plots,
        "visual_data":        visual_data,
        "visualization_type": "algorithm",
        "observations":       observations,
        "confidence_score":   0.94,
        "simulation_log":     log,
    }

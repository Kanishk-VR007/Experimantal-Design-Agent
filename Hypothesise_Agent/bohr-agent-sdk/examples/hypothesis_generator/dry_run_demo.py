#!/usr/bin/env python3
"""
Dry Run Demo Script
===================
Quick demonstration of the dry run feature with various experiment examples.

Usage:
    python dry_run_demo.py
    python dry_run_demo.py --custom "Your experiment title here"
"""
import subprocess
import sys
import os

# Example experiment titles to demonstrate
EXAMPLE_EXPERIMENTS = [
    "Compare CNN vs Transformer models on image classification",
    "Effect of learning rate on neural network convergence",
    "LSTM vs GRU for time series prediction",
    "Impact of batch normalization on deep learning model performance",
    "Comparison of optimization algorithms for training deep networks",
]


def run_dry_run(experiment_title: str):
    """Execute dry run for a given experiment title."""
    script_path = os.path.join(os.path.dirname(__file__), "hypo_agent.py")
    
    cmd = [
        sys.executable,
        script_path,
        "--dry-run",
        "--experiment",
        experiment_title
    ]
    
    subprocess.run(cmd)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--custom":
        # Run custom experiment
        if len(sys.argv) < 3:
            print("Error: Please provide an experiment title after --custom")
            sys.exit(1)
        experiment = " ".join(sys.argv[2:])
        run_dry_run(experiment)
    else:
        # Interactive mode: let user choose from examples
        print("\n" + "=" * 72)
        print("  DRY RUN DEMO - Hypothesis Generator")
        print("=" * 72)
        print("\nSelect an experiment to simulate:")
        
        for i, exp in enumerate(EXAMPLE_EXPERIMENTS, 1):
            print(f"  {i}. {exp}")
        print(f"  {len(EXAMPLE_EXPERIMENTS) + 1}. Enter custom experiment")
        
        try:
            choice = input("\nYour choice (1-{}): ".format(len(EXAMPLE_EXPERIMENTS) + 1)).strip()
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(EXAMPLE_EXPERIMENTS):
                experiment = EXAMPLE_EXPERIMENTS[choice_num - 1]
                run_dry_run(experiment)
            elif choice_num == len(EXAMPLE_EXPERIMENTS) + 1:
                custom = input("\nEnter your experiment title: ").strip()
                if custom:
                    run_dry_run(custom)
                else:
                    print("Error: Empty experiment title")
            else:
                print("Invalid choice")
        except ValueError:
            print("Invalid input")
        except KeyboardInterrupt:
            print("\n\nAborted by user")


if __name__ == "__main__":
    main()

"""Preserve Terraform variable spelling when Python reads Windows environments."""

import os


def terraform_environment():
    # Windows os.environ uppercases keys; this project's input names are lowercase.
    return {
        "TF_VAR_" + key[7:].lower() if key.upper().startswith("TF_VAR_") else key: value
        for key, value in os.environ.items()
    }

#!/bin/bash
# Build the NOMS paper using latexmk
cd $(dirname "$0")
latexmk -pdf ieee2026.tex

# Software citations and acknowledgements

[Home](../README.md) · [User manual](MANUAL.md) · [Command reference](COMMANDS.md)

## What to cite

| Calculation | References to include when used |
|---|---|
| All workflows | MolForge software record and installed version |
| Conformers / selection | RDKit; Open Babel if used |
| AutoDock docking | Meeko, gemmi, AutoDock-GPU, AutoGrid / AutoDock4 |
| Receptor repair | PDBFixer, OpenMM |
| MD / MM/GBSA | Uni-GBSA, GROMACS, AmberTools; ACPYPE and gmx_MMPBSA when used |
| Macromolecular docking | HDOCK |

MolForge coordinates independent scientific programs; it does not bundle their code,
binaries, force fields, or model data. Cite every program that actually contributed to
the reported result. GitHub's **Cite this repository** control reads
[`CITATION.cff`](../CITATION.cff) for
the MolForge citation. That citation does not replace the package citations below.

Record exact versions from the job's `environment.json`, engine logs, and package
environment. For a reproducible software inventory, retain:

```bash
python -m pip freeze > python-packages.txt
gmx --version > gromacs-version.txt 2>&1
```

Version-specific software records take precedence when a project supplies one. For
example, RDKit asks users to cite its website and the Zenodo DOI for the exact release,
and GROMACS publishes a versioned software DOI and manual DOI. The references below
follow the upstream projects' current citation instructions.

## Conformer generation and structure handling

- **RDKit** — used directly for SMILES parsing, ETKDGv3 embedding, MMFF94s
  minimization, diversity filtering, and SDF handling. Cite *RDKit: Open-source
  cheminformatics*, https://www.rdkit.org, plus the DOI for the installed release from
  https://doi.org/10.5281/zenodo.591637.
- **Open Babel** — invoked only when optional PDBQT export is requested. Cite
  O'Boyle, N. M. et al. *Open Babel: An open chemical toolbox.* Journal of
  Cheminformatics **3**, 33 (2011). https://doi.org/10.1186/1758-2946-3-33, and report
  the Open Babel version as requested by its documentation.
- **gemmi** — installed with the docking extra and used by Meeko's receptor workflow.
  Cite Wojdyr, M. *GEMMI: A library for structural biology.* Journal of Open Source
  Software **7**, 4200 (2022). https://doi.org/10.21105/joss.04200.

## AutoDock workflow

- **Meeko** — prepares ligand and receptor inputs and exports docking poses. Cite
  Santos-Martins, D. et al. *Meeko: Molecule Parametrization and Software
  Interoperability for Docking and Beyond.* Journal of Chemical Information and
  Modeling (2025). https://doi.org/10.1021/acs.jcim.5c02271.
- **AutoDock-GPU** — performs the docking search. Cite Santos-Martins, D. et al.
  *Accelerating AutoDock4 with GPUs and Gradient-Based Local Search.* Journal of
  Chemical Theory and Computation **17**, 1060–1073 (2021).
  https://doi.org/10.1021/acs.jctc.0c01006.
- **AutoGrid4 / AutoDock4** — generates AutoDock affinity maps and supplies the
  underlying AutoDock4 method. Cite Morris, G. M. et al. *AutoDock4 and
  AutoDockTools4: Automated Docking with Selective Receptor Flexibility.* Journal of
  Computational Chemistry **30**, 2785–2791 (2009).
  https://doi.org/10.1002/jcc.21256.

## Receptor repair

- **PDBFixer** — identifies and repairs missing atoms and adds hydrogens. PDBFixer does
  not currently publish a separate scholarly citation; identify the package, exact
  version, and project URL: https://github.com/openmm/pdbfixer. Its upstream source
  identifies it as part of the OpenMM toolkit.
- **OpenMM** — provides the molecular structure API used by PDBFixer. The OpenMM user
  guide asks all work using OpenMM to cite Eastman, P. et al. *OpenMM 8: Molecular
  Dynamics Simulation with Machine Learning Potentials.* Journal of Physical
  Chemistry B **128**, 109–116 (2024). https://doi.org/10.1021/acs.jpcb.3c06662.

## Molecular dynamics and MM/GBSA

- **Uni-GBSA** — drives system preparation, MD, and MM/GB(PB)SA analysis. Cite Yang,
  M. et al. *Uni-GBSA: an open-source and web-based automatic workflow to perform
  MM/GB(PB)SA calculations for virtual screening.* Briefings in Bioinformatics
  **24**, bbad218 (2023). https://doi.org/10.1093/bib/bbad218.
- **GROMACS** — runs MD and trajectory conversion. Cite the papers selected by the
  GROMACS team for the features used; a standard general reference is Abraham, M. J.
  et al. *GROMACS: High performance molecular simulations through multi-level
  parallelism from laptops to supercomputers.* SoftwareX **1–2**, 19–25 (2015).
  https://doi.org/10.1016/j.softx.2015.06.001. Also use the source-code and manual DOIs
  for the installed GROMACS release listed in its corresponding reference manual.
- **AmberTools** — supplies ligand parameterization and MM/GBSA components used by a
  typical Uni-GBSA installation. Cite Case, D. A. et al. *AmberTools.* Journal of
  Chemical Information and Modeling **63**, 6183–6191 (2023).
  https://doi.org/10.1021/acs.jcim.3c01153, and consult the installed AmberTools manual
  for method-specific citations such as GAFF/GAFF2 and AM1-BCC.
- **ACPYPE**, when present in the Uni-GBSA execution path — cite Sousa da Silva,
  A. W. & Vranken, W. F. *ACPYPE—AnteChamber PYthon Parser interfacE.* BMC Research
  Notes **5**, 367 (2012). https://doi.org/10.1186/1756-0500-5-367.
- **gmx_MMPBSA**, when present in the Uni-GBSA analysis path — cite Valdés-Tresanco,
  M. S. et al. *gmx_MMPBSA: A New Tool to Perform End-State Free Energy Calculations
  with GROMACS.* Journal of Chemical Theory and Computation **17**, 6281–6291 (2021).
  https://doi.org/10.1021/acs.jctc.1c00645. Its documentation also requests citation
  of MMPBSA.py when that implementation contributes to the analysis.

## HDOCK workflow

- **HDOCK / HDOCKlite** — performs macromolecular docking through separately obtained
  local executables. Cite Yan, Y., Tao, H., He, J. & Huang, S.-Y. *The HDOCK server
  for integrated protein–protein docking.* Nature Protocols **15**, 1829–1852 (2020).
  https://doi.org/10.1038/s41596-020-0312-x. HDOCKlite is not bundled with MolForge;
  check its own download terms before redistribution.

## Development and packaging tools

The repository's automated checks use Python, setuptools, PyPA build, pytest, and
GitHub Actions. They do not contribute to molecular results, and their upstream
projects do not request scientific-paper citations for ordinary use. Preserve their
names and versions in development or build provenance when exact reproducibility is
required: https://www.python.org, https://setuptools.pypa.io,
https://build.pypa.io, https://pytest.org, and https://github.com/features/actions.

## License responsibility

The MolForge MIT license applies only to MolForge-owned source. Each dependency and
external executable remains under its upstream license. Dependency versions and
licenses can change independently, so review the installed package metadata and the
upstream license before redistribution. Scientific citation and software-license
compliance are separate obligations.

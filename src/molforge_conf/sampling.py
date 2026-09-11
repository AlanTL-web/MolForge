"""Bounded multi-round sampling and energy-ordered post-minimization diversity."""
import math
from rdkit import Chem
from rdkit.Chem import AllChem, rdMolAlign


def sample(molecule, count, seed, threshold, max_iters, rounds, embedding_attempts=100,
           progress=None, random_coordinates_only=False, threads=4):
    ensemble = Chem.Mol(molecule)
    ensemble.RemoveAllConformers()
    candidates, reports = [], []
    standard_failed = False
    names = ('randomSeed', 'pruneRmsThresh', 'useRandomCoords', 'maxIterations',
             'useSmallRingTorsions', 'useMacrocycleTorsions', 'useMacrocycle14config',
             'enforceChirality', 'forceTransAmides', 'onlyHeavyAtomsForRMS',
             'useSymmetryForPruning', 'numThreads')
    for index in range(rounds):
        work = Chem.Mol(molecule)
        params = AllChem.ETKDGv3()
        params.randomSeed = (seed + index * 104729) % 2147483647 if seed >= 0 else -1
        params.pruneRmsThresh = threshold
        params.maxIterations = embedding_attempts
        params.useRandomCoords = random_coordinates_only or standard_failed or bool(index % 2)
        params.numThreads = threads
        params.trackFailures = True
        supported_names = tuple(name for name in names if hasattr(params, name))
        requested = {name: getattr(params, name) for name in supported_names}
        ids = list(AllChem.EmbedMultipleConfs(work, numConfs=count, params=params))
        if not ids and not params.useRandomCoords:
            standard_failed = True
        results = AllChem.MMFFOptimizeMoleculeConfs(
            work, numThreads=threads, maxIters=max_iters, mmffVariant='MMFF94s') if ids else []
        retried, accepted, energies = 0, 0, []
        props = AllChem.MMFFGetMoleculeProperties(work, mmffVariant='MMFF94s') if ids else None
        for conf_id, (status, energy) in zip(ids, results):
            if status == 1:
                forcefield = AllChem.MMFFGetMoleculeForceField(work, props, confId=conf_id)
                status = forcefield.Minimize(maxIts=max_iters)
                energy = forcefield.CalcEnergy()
                retried += 1
            valid = status == 0 and math.isfinite(energy)
            identity = ensemble.AddConformer(Chem.Conformer(work.GetConformer(conf_id)), assignId=True)
            candidates.append((identity, status, float(energy)))
            if valid:
                accepted += 1
                energies.append(float(energy))
        reports.append(dict(round=index + 1, embedding_parameters=requested,
            resolved_embedding_parameters={name: getattr(params, name) for name in supported_names},
            embedding_failure_counts=list(params.GetFailureCounts()),
            embedded=len(ids), optimization_retries=retried, converged=accepted,
            minimum_energy=min(energies) if energies else None))
        if progress:
            progress(reports)
    return ensemble, candidates, reports


def select_diverse(molecule, candidates, threshold, limit):
    """Keep lowest-energy converged candidates, then enforce heavy-atom RMSD.

    Symmetry matching is bounded at 256 matches; this is an approximate diversity
    screen for highly symmetric molecules, not an exhaustive symmetry search.
    Alignment mutates only a hydrogen-stripped copy used for comparisons.
    """
    heavy = Chem.RemoveHs(Chem.Mol(molecule))
    selected, duplicates = [], 0
    valid = sorted((row for row in candidates if row[1] == 0 and math.isfinite(row[2])),
                   key=lambda row: (row[2], row[0]))
    for row in valid:
        if threshold > 0 and any(rdMolAlign.GetBestRMS(
                heavy, heavy, prbId=row[0], refId=other[0], maxMatches=256) < threshold
                for other in selected):
            duplicates += 1
            continue
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected, duplicates

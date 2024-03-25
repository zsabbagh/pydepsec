import subprocess, datetime, os, json, lizard, glob, time
from pathlib import Path
from pprint import pprint
from loguru import logger
# This file includes the running of other programmes or modules

def get_files(dir: str, includes: list = None, excludes: list = None, file_pattern: str = '*.py') -> list:
    """
    Get all files in a directory, optionally filtered by includes and excludes.
    """
    dir = Path(dir).absolute()
    if not dir.exists():
        logger.error(f"Directory '{dir}' does not exist!")
        return []
    files = []
    excs = [ Path(dir / e).absolute() for e in ([excludes] if type(excludes) == str else excludes) ] if excludes else []
    incs = [ Path(dir / i).absolute() for i in ([includes] if type(includes) == str else includes) ] if includes else [dir]
    for i in incs:
        skip = False
        for exc in excs:
            if str(i.absolute()).startswith(str(exc.absolute())):
                skip = True
                break
        if skip:
            continue
        for f in i.glob(f'**/{file_pattern}'):
            if f.is_file():
                files.append(f)
    return files

def run_lizard(dir: str | Path, includes: list = None, excludes: list = None) -> dict:
    """
    Runs Lizard on the codebase provided.

    dir: str | Path: The directory to run Lizard on.
    includes: list: The filepaths to include.
    excludes: list: The filepaths to exclude (starting with the directory provided).
    """
    files = get_files(dir, includes, excludes)
    nloc = 0
    ccn = 0
    functions = 0
    for file in files:
        # we check all files
        # do not remove test or __init__.py files unless stated in excludes
        file = Path(file)
        lizard_result = lizard.analyze_file(str(file))
        nloc += lizard_result.nloc
        for func in lizard_result.function_list:
            ccn += func.cyclomatic_complexity
            functions += 1
    ccn_avg = ccn / functions if functions > 0 else 0
    nloc_avg = nloc / functions if functions > 0 else 0
    return {
        'nloc': nloc,
        'nloc_average': nloc_avg,
        'ccn_average': ccn_avg,
        'files': len(files),
        'functions': functions
    }

def run_bandit(dir: str | Path,
               includes: str | list = None,
               excludes: str | list = None,
               output: str | Path = None) -> None:
    """
    Run Bandit on the codebase.

    dir: str | Path: The directory to run Bandit on.
    includes: str | list: The filepaths to include.
    excludes: str | list: The filepaths to exclude (starting with the directory provided).
    output: str | Path: The output directory for the Bandit results.

    returns:
    dict: The Bandit results for each directory.
    """
    # Run Bandit
    dir = Path(dir).absolute()
    includes = [includes] if type(includes) == str else ( includes if type(includes) == list else [] )
    includes = [ Path(dir / i).absolute() for i in includes ] if includes else [dir]
    excludes = [excludes] if type(excludes) == str else ( excludes if type(excludes) == list else [] )
    result = {}
    output_dir = Path(output).absolute() if output else Path(os.getcwd()) / '__temp__'
    if not output_dir.parent.exists():
        logger.error(f"Output directory '{output_dir.parent}' does not exist!")
        exit(1)
    if not output_dir.exists():
        output_dir.mkdir()
    processed_dirs = set()
    counted_files = set()
    loc = nosec = skipped_tests = 0
    total_issues = 0
    h_sev = m_sev = l_sev = u_sev = 0
    h_conf = m_conf = l_conf = u_conf = 0
    sev_conf = {}
    all_issues = []
    files_skipped = 0
    for incldir in includes:
        skipdir = False
        for procdir in processed_dirs:
            if str(incldir.absolute()).startswith(str(procdir)):
                logger.warning(f"Skipping directory '{incldir.absolute()}' as it has already been counted.")
                skipdir = True
                break
        if skipdir:
            continue
        processed_dirs.add(str(incldir.absolute()))
        dirname = str(incldir).lstrip(str(dir.absolute()))
        if dirname == '':
            dirname = dir.absolute().name
        result[dirname] = {}
        dt = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        fn = output_dir / f'bandit-{dt}.json'
        if not incldir.exists():
            logger.debug(f"Skipping '{incldir}' as it does not exist.")
            continue
        logger.info("Running Bandit...")
        data = None
        try:
            subprocess.run(["bandit", "-r", str(incldir), '-f', 'json', '-o', str(fn)])
            with open(fn, 'r') as f:
                data = json.load(f)
                for err in data.get('errors', []):
                    if err.get('filename') is not None:
                        files_skipped += 1
                issues = data.get('results', [])
                for issue in issues:
                    filename = issue.get('filename')
                    if filename is not None:
                        counted_files.add(filename)
                    # count issues
                    sev = issue.get('issue_severity', 'undefined').lower()
                    conf = issue.get('issue_confidence', 'undefined').lower()
                    if sev not in sev_conf:
                        sev_conf[sev] = {}
                    if conf not in sev_conf[sev]:
                        sev_conf[sev][conf] = 0
                    sev_conf[sev][conf] += 1
                    all_issues.append(issue)
                total_issues += len(issues)
                totalcount = data.get('metrics', {}).get('_totals', {})
                loc += totalcount.get('loc', 0)
                nosec += totalcount.get('nosec', 0)
                skipped_tests += totalcount.get('skipped_tests', 0)
                h_sev += totalcount.get('SEVERITY.HIGH', 0)
                m_sev += totalcount.get('SEVERITY.MEDIUM', 0)
                l_sev += totalcount.get('SEVERITY.LOW', 0)
                u_sev += totalcount.get('SEVERITY.UNDEFINED', 0)
                h_conf += totalcount.get('CONFIDENCE.HIGH', 0)
                m_conf += totalcount.get('CONFIDENCE.MEDIUM', 0)
                l_conf += totalcount.get('CONFIDENCE.LOW', 0)
                u_conf += totalcount.get('CONFIDENCE.UNDEFINED', 0)
                try:
                    fn.unlink()
                except Exception as e:
                    logger.error(f"Could not delete file '{fn}': {e}")
        except Exception as e:
            logger.error(f"Bandit found issues in the codebase: {e}")
            continue
    return {
        'issues': all_issues,
        'loc': loc,
        'nosec': nosec,
        'skipped_tests': skipped_tests,
        'issues_total': len(all_issues),
        'files_counted': len(counted_files),
        'files_skipped': files_skipped,
        'confidence_high_count': h_conf,
        'confidence_medium_count': m_conf,
        'confidence_low_count': l_conf,
        'confidence_undefined_count': u_conf,
        'severity_high_count': h_sev,
        'severity_medium_count': m_sev,
        'severity_low_count': l_sev,
        'severity_undefined_count': u_sev,
        'severity_confidence': sev_conf,
    }

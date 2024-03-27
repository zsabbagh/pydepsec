import numpy as np
import src.utils.db as db
from copy import deepcopy
from loguru import logger

def _get_entry(*args, element='entry'):
    if element != 'entry':
        return args[2]
    return args[1]

def _get_data(*args):
    return args[0]

def impact_to_int(score: str):
    """
    Translates a CVSS score to an integer
    """
    if score is None:
        return None
    elif type(score) in [int, float]:
        return score
    score = score.lower()
    match score:
        case 'none':
            return 0
        case 'low' | 'partial':
            return 1
        case 'high' | 'complete':
            return 2
    return None

def patch_lag(data: dict, entry: dict, *args, format='days', start: str = 'release'):
    """
    Asserts that the data has 'cves' and 'releases' keys.
    """
    releases = entry.get('release', {})
    releases = releases if type(releases) == list else [releases]
    cves = data.get('cves', {})
    entry_cves = entry.get('cves', {})
    values = []
    for rel in releases:
        rel_published_at = data.get('releases', {}).get(rel, {}).get('published_at')
        for cve in entry_cves:
            cve = cves.get(cve)
            apps = cve.get('applicability', [])
            for app in apps:
                if db.is_applicable(rel, app):
                    patched_at = app.get('patched_at')
                    start = rel_published_at if start == 'release' else cve.get('published_at')
                    if patched_at and start:
                        diff = (patched_at - start).days
                        diff = diff / 30.0 if format == 'months' else (
                            diff / 365.0 if format == 'years' else diff
                        )
                        values.append(diff)
    return values

def cves_per_nloc(data: dict, entry: dict, *args):
    """
    CVEs per 10k NLOC
    """
    rels = entry.get('release', [])
    rels = rels if type(rels) == list else [rels]
    total_nloc = 0
    releases = data.get('releases', {})
    for rel in rels:
        nloc = releases.get(rel, {}).get('nloc_total', 0)
        if nloc:
            total_nloc += nloc
    total_cves = len(entry.get('cves', []))
    return total_cves / (total_nloc / 10000.0) if total_nloc else None

# This file helps with computing KPIs for certain data structures
# *args are in the order (data, elem, entry)
KPIS = {
    'base': {
        'default': 'mean',
        'key': 'cvss_base_score',
        'max': 10,
        'element': 'cve',
        'title': 'CVSS Base Score',
        'y_label': 'Score',
    },
    'releases': {
        'default': 'sum',
        # first is data, second is the element
        'key': lambda *args: len(args[1].get('release', [])) if type(args[1].get('release')) == list else 1,
        'title': 'Number of Releases',
        'element': 'entry',
        'suffix': 'total',
        'y_label': 'Count',
    },
    'lag/release': {
        'default': 'mean',
        'returns_values': True,
        'key': lambda *args : patch_lag(*args, format='days'),
        'title': 'Days: Release to Patched Release',
        'fill': False,
        'element': 'cve',
        'y_label': 'Days',
    },
    'lag/cve': {
        'default': 'mean',
        'returns_values': True,
        'key': lambda *args : patch_lag(*args, format='days', start='cve'),
        'title': 'Days: CVE Published to Patched Release',
        'fill': False,
        'element': 'cve',
        'y_label': 'Days',
    },
    'issues': {
        'default': 'sum',
        'key': lambda *args: args[1].get('bandit_report', {}).get('issues_total'), # return None to ignore the entry
        'title': 'Bandit Issues',
        'element': 'release',
        'y_label': 'Count',
    },
    'files': {
        'default': 'sum', # all files for all releases (generalise for dependencies)
        'key': 'counted_files', # TODO: inconsistent naming, should be files_counted
        'title': 'Number of Files',
        'element': 'release',
        'y_label': 'Count',
    },
    'functions': {
        'default': 'sum',
        'key': 'counted_functions',
        'title': 'Number of Functions',
        'element': 'release',
        'y_label': 'Count',
    },
    'impact': {
        'default': 'mean',
        'key': 'cvss_impact_score',
        'title': 'CVSS Impact Score',
        'max': 10,
        'element': 'cve',
        'y_label': 'Score',
    },
    'exploitability': {
        'default': 'mean',
        'key': 'cvss_exploitability_score',
        'title': 'CVSS Exploitability Score',
        'max': 10,
        'element': 'cve',
        'y_label': 'Score',
    },
    'confidentiality': {
        'default': 'mean', # mean impact of all CVEs
        'key': lambda *args: impact_to_int(args[1].get('cvss_confidentiality_impact')),
        'title': 'CVSS Confidentiality Impact',
        'max': 2,
        'element': 'cve',
        'y_label': 'Impact',
    },
    'integrity': {
        'default': 'mean',
        'key': lambda *args: impact_to_int(args[1].get('cvss_integrity_impact')),
        'title': 'CVSS Integrity Impact',
        'max': 2,
        'element': 'cve',
        'y_label': 'Impact',
    },
    'availability': {
        'default': 'mean',
        'key': lambda *args: impact_to_int(args[1].get('cvss_availability_impact')),
        'title': 'CVSS Availability Impact',
        'max': 2,
        'element': 'cve',
        'y_label': 'Impact',
    },
    'cves': {
        'default': 'sum', # sum of all CVEs for all releases
        'suffix': 'total', # suffix of the legend description
        # assume that the key is a function that takes (data, elem) as arguments
        'key': lambda *args: len(args[1].get('cves', [])),
        'title': 'Number of CVEs',
        'element': 'entry',
        'y_label': 'Count',
    },
    'nloc': {
        'default': 'sum',
        'key': 'nloc_total',
        'title': 'Number of Lines of Code (NLOC)',
        'element': 'release', # 'entry' or 'release
        'y_label': 'NLOC',
    },
    'cves/nloc': {
        'default': 'sum',
        'key': lambda *args: cves_per_nloc(*args),
        'element': 'entry',
        'title': 'CVEs per 10k NLOC',
        'y_label': 'CVEs per 10k NLOC',
    },
    'ccn': {
        'default': 'mean',
        'key': 'ccn_average',
        'title': 'Cyclomatic Complexity (CCN) / Function',
        'element': 'release',
        'y_label': 'CCN',
    },
}

def values_to_stats(list_of_values: list):
    """
    Converts a list of values to a dictionary of statistics.
    """
    result = {
        'sum': [],
        'mean': [],
        'std': [],
        'min': [],
        'max': [],
    }
    for values in list_of_values:
        if not values:
            for k in result:
                result[k].append(None)
        else:
            result['sum'].append(np.sum(values))
            result['mean'].append(np.mean(values))
            result['std'].append(np.std(values))
            result['min'].append(np.min(values))
            result['max'].append(np.max(values))
    return result
    

def timeline_kpis(data: dict, *kpis: str):
    """
    Computes KPIs for a timeline data structure.
    """
    cves = data.get('cves', {})
    releases = data.get('releases', {})
    timeline = data.get('timeline')
    cves = data.get('cves')
    results = {
        k: deepcopy(KPIS[k]) for k in kpis if k in KPIS
    }
    dates = []
    kpi_args = list(kpis)
    kpi_argset = set(kpi_args)
    # first, we compute release-related KPIs
    for entry in timeline:
        dates.append(entry.get('date'))
        rel = entry.get('release')
        # make sure we have a list of releases, even if it is a single release
        # this is to make the code more extensible
        relvs = [rel] if type(rel) == str else rel
        if type(relvs) != list:
            logger.error(f"Unexpected release type: {type(relvs).__name__}")
            continue
        for k in results:
            if k not in kpi_argset:
                continue
            # expect keywords type, element, function
            kpi: dict = KPIS.get(k)
            element_name: str = kpi.get('element')
            element = ids = None
            if 'values' not in results[k]:
                results[k]['values'] = []
            returns_values = kpi.get('returns_values')
            if returns_values:
                logger.info(f"Returns values for KPI '{k}'")
                key = kpi.get('key')
                if not callable(key):
                    logger.error(f"Expected function for KPI '{k}'")
                    continue
                try:
                    values = key(data, entry)
                    results[k]['values'].append(values)
                    continue
                except Exception as e:
                    logger.error(f"Could not compute KPI '{k}': {e}")
                    continue
            match element_name:
                case 'cve':
                    element = cves
                    ids = entry.get('cves')
                case 'entry':
                    element = entry
                case 'release':
                    element = releases
                    ids = relvs
                case _:
                    logger.error(f"Unexpected element name: {element_name}")
                    continue
            # if ids is None, we assume the element is a list of elements or an element
            if ids is None:
                ids = element if type(element) == list else [element]
            scores = []
            for id in ids:
                elem = id if type(id) == dict else (
                    element.get(id) if type(id) == str else None
                )
                if elem is None:
                    logger.error(f"Could not find {element} for {id}")
                    continue
                key = kpi.get('key')
                if key is None:
                    logger.error(f"Could not find function for KPI '{k}'")
                    continue
                if type(key) == str:
                    # when given a string, the key is a dictionary key
                    val = elem.get(key)
                    if val:
                        scores.append(val)
                    else:
                        logger.info(f"Could not find key '{key}' for {id}")
                        scores.append(None)
                elif callable(key):
                    # when given a function, the key is a function with args (data, elem)
                    try:
                        value = key(data, elem)
                        scores.append(value)
                    except Exception as e:
                        logger.error(f"Could not compute KPI '{k}' for {id}: {e}")
                        continue
                else:
                    logger.error(f"Unexpected function type: {type(key).__name__}")
                    continue
            scores = [s for s in scores if s is not None]
            results[k]['values'].append(scores)
    # then we compute the KPIs for the CVEs
    results['dates'] = dates
    return results

def overall_kpis(data: dict, *kpis):
    pass
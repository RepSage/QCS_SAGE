# -*- coding: utf-8 -*-
"""Run the batch qualification for a whole semester: every site that has HOBO
   or Seaguard data in it. Usage: run_semester.py 2019S1"""
import sys, os, re, importlib.util, warnings
warnings.filterwarnings('ignore')
S = os.path.dirname(os.path.abspath(__file__))     # qualify_site.py lives beside this file

# read the argument BEFORE clearing sys.argv for the import below - reading it
# after silently fell back to the default and re-ran the wrong semester
if len(sys.argv) < 2 or not re.fullmatch(r'\d{4}S[12]', sys.argv[1]):
    raise SystemExit('usage: run_semester.py <YEAR>S<1|2>   (e.g. 2020S1)')
sem = sys.argv[1]

spec = importlib.util.spec_from_file_location('qs', os.path.join(S, 'qualify_site.py'))
qs = importlib.util.module_from_spec(spec)
sys.argv = ['qualify_site.py']          # keep its __main__ guard quiet
spec.loader.exec_module(qs)

sites = set()
for camp in os.listdir(qs.SG_RAW):
    p = os.path.join(qs.SG_RAW, camp)
    if os.path.isdir(p) and qs.sem_tag(camp) == sem:
        sites.update(d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d)))
# HOBO is campaign-first (like Seaguard) since the 2026-08-13 reorganisation:
# HOBO\raw\<RRDM campaign>\<site>. The _ buckets never match sem_tag.
for camp in os.listdir(qs.H_RAW):
    p = os.path.join(qs.H_RAW, camp)
    if os.path.isdir(p) and qs.sem_tag(camp) == sem:
        sites.update(d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d)))

sites = sorted(sites)
print("=== SEMESTER %s : %d site(s) ===" % (sem, len(sites)))
print("   ", ', '.join(sites), "\n")
total, failed = [], []
for i, site in enumerate(sites, 1):
    print("\n----- [%d/%d] %s -----" % (i, len(sites), site))
    try:
        res = qs.do_site(site, sem)
    except Exception as e:
        import traceback; traceback.print_exc(); failed.append((site, str(e)[:80])); continue
    for name, fc, n, err in res:
        (total if fc else failed).append((name, n if fc else err))

# the two HOBO-only buckets (_PISCINAS / _EXPERIMENTOS) sit outside the site tree
if os.environ.get('QCS_SG_ONLY'):
    print("\n(QCS_SG_ONLY: HOBO buckets skipped)")
else:
    print("\n----- buckets (_PISCINAS / _EXPERIMENTOS) -----")
    try:
        for name, fc, n, err in qs.do_buckets(sem):
            (total if fc else failed).append((name, n if fc else err))
    except Exception as e:
        import traceback; traceback.print_exc(); failed.append(('BUCKETS', str(e)[:80]))

print("\n\n================ SEMESTER %s SUMMARY ================" % sem)
print("products OK : %d" % len(total))
print("failed      : %d" % len(failed))
for n, k in total:
    print("  OK   %-48s %s panel(s)" % (n, k))
for n, e in failed:
    print("  FAIL %-48s %s" % (n, e))

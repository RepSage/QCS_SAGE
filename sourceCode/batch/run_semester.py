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
for raw in (qs.SG_RAW, qs.H_RAW):
    p = os.path.join(raw, sem)
    if os.path.isdir(p):
        sites.update(
            d for d in os.listdir(p)
            if os.path.isdir(os.path.join(p, d))
            and d.upper() != '_SEM_SITIO'
            and not d.upper().startswith('PISCINA_')
        )

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

print("\n\n================ SEMESTER %s SUMMARY ================" % sem)
print("products OK : %d" % len(total))
print("failed      : %d" % len(failed))
for n, k in total:
    print("  OK   %-48s %s panel(s)" % (n, k))
for n, e in failed:
    print("  FAIL %-48s %s" % (n, e))

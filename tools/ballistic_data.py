"""Carga las tablas de data/ (shells, penetration, materials), valida y
consulta la penetracion interpolada.

Sin dependencias: solo la biblioteca estandar.
Uso:  python ballistic_data.py data/           lista lo cargado y avisa de huecos
      python ballistic_data.py --selftest
"""
import csv
import math
import os
import sys


def _num(s, where=''):
    """Celda a float, o None si esta vacia. Acepta coma decimal."""
    raw = (s or '').strip()
    if not raw:
        return None
    try:
        return float(raw.replace(',', '.'))
    except ValueError:
        raise ValueError(
            f"celda no numerica: '{raw}'{where}. Si viene de Google Sheets, "
            "revisa que no lleve separador de miles ni unidades ('80 mm' -> '80').")


class BallisticData:
    def __init__(self, folder):
        self.projectiles = {}
        self.materials = {}
        self.table = {}        # projectile_id -> {angle: {distance: mm}}
        self.meta = {}         # projectile_id -> (angle_from, thickness_basis, criterion)
        self.warnings = []
        self._load(folder)

    # --- carga --------------------------------------------------------------
    def _rows(self, folder, *names):
        """Primer fichero que exista de los nombres dados."""
        for name in names:
            path = os.path.join(folder, name)
            if os.path.exists(path):
                break
        else:
            raise FileNotFoundError(
                f"no encuentro ninguno de {names} en {folder}")
        with open(path, newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    def _load(self, folder):
        for r in self._rows(folder, 'shells.csv', 'projectiles.csv'):
            r['id'] = r.get('shell_id') or r.get('id')
            for k in ('caliber_mm', 'mass_kg', 'muzzle_velocity_ms',
                      'explosive_mass_g', 'fuze_delay_ms',
                      'core_mass_kg', 'core_mass_g'):
                r[k] = _num(r.get(k))
            if r['core_mass_kg'] is None and r['core_mass_g'] is not None:
                r['core_mass_kg'] = r['core_mass_g'] / 1000.0
            # masa que de verdad penetra: el nucleo en APCR, el proyectil entero si no
            r['penetrating_mass_kg'] = r['core_mass_kg'] or r['mass_kg']
            if r['core_mass_kg'] is not None and r['mass_kg'] and \
                    r['core_mass_kg'] > r['mass_kg']:
                self.warnings.append(
                    f"{r['id']}: el nucleo ({r['core_mass_kg']} kg) pesa mas que "
                    f"el proyectil ({r['mass_kg']} kg); revisa las unidades")
            if r['core_mass_kg'] is not None and r['mass_kg'] and \
                    r['core_mass_kg'] < r['mass_kg'] / 100.0:
                self.warnings.append(
                    f"{r['id']}: el nucleo es {r['core_mass_kg']*1000:.1f} g frente a "
                    f"{r['mass_kg']} kg de proyectil; revisa si la columna es g o kg")
            for k, lo, hi in (('caliber_mm', 10, 300), ('mass_kg', 0.1, 100),
                              ('muzzle_velocity_ms', 100, 2000)):
                if r[k] is not None and not lo <= r[k] <= hi:
                    self.warnings.append(
                        f"{r['id']}: {k} = {r[k]} esta fuera de lo plausible "
                        f"({lo}-{hi}); revisa el separador decimal")
            self.projectiles[r['id']] = r
            if r['explosive_mass_g'] is None:
                self.warnings.append(f"{r['id']}: explosive_mass_g vacio")
            elif r['explosive_mass_g'] and r['fuze_delay_ms'] is None:
                self.warnings.append(
                    f"{r['id']}: lleva explosivo pero no tiene fuze_delay_ms")
            if r['type'] == 'APCR' and r['core_mass_kg'] is None:
                self.warnings.append(
                    f"{r['id']}: APCR sin core_mass_g; se usa la masa total "
                    f"y el spall sale bajo")

        for r in self._rows(folder, 'materials.csv'):
            r['resistance'] = _num(r['resistance'])
            r['spall'] = _num(r['spall'])
            self.materials[r['id']] = r
            if r['resistance'] is None:
                self.warnings.append(f"material {r['id']}: sin resistance")

        known = set(self.projectiles)
        seen = set()
        for r in self._rows(folder, 'penetration.csv'):
            pid = r.get('shell_id') or r.get('projectile_id')
            seen.add(pid)
            mm = _num(r['penetration_mm'])
            src = (r.get('source') or '').strip()
            if mm is None:
                self.warnings.append(
                    f"{pid} {r['distance_m']}m {r['angle_deg']}deg: sin valor"
                    + (f" -- {src}" if src else ""))
                continue
            if src.upper().startswith('REVISAR'):
                self.warnings.append(f"{pid} {r['distance_m']}m {r['angle_deg']}deg: {src}")
            if not 5.0 <= mm <= 1000.0:
                self.warnings.append(
                    f"{pid} {r['distance_m']}m {r['angle_deg']}deg: {mm} mm es "
                    "implausible; revisa el separador decimal o de miles")
            a, d = _num(r['angle_deg']), _num(r['distance_m'])
            self.table.setdefault(pid, {}).setdefault(a, {})[d] = mm
            prev = self.meta.get(pid)
            cur = ((r.get('angle_from') or '').strip(),
                   (r.get('thickness_basis') or '').strip(),
                   (r.get('criterion') or '').strip())
            if prev and prev != cur:
                self.warnings.append(f"{pid}: convenciones mezcladas {prev} vs {cur}")
            self.meta[pid] = cur

        for pid in sorted(seen - known):
            self.warnings.append(
                f"ERROR: penetration.csv usa '{pid}', que no esta en shells.csv")
        for pid in sorted(known - seen):
            self.warnings.append(f"{pid}: sin filas en penetration.csv")

        for pid, (af, tb, cr) in self.meta.items():
            if not af:
                self.warnings.append(f"{pid}: angle_from sin definir")
            if not tb:
                self.warnings.append(f"{pid}: thickness_basis sin definir (se supone 'nominal')")
            if not cr:
                self.warnings.append(f"{pid}: criterion sin definir")

    # --- consulta -----------------------------------------------------------
    @staticmethod
    def _interp(pairs, x):
        """Interpola en una lista [(x, y)] ordenada. Devuelve (y, extrapolado)."""
        if not pairs:
            return None, False
        if len(pairs) == 1:
            return pairs[0][1], x != pairs[0][0]
        if x <= pairs[0][0]:
            (x0, y0), (x1, y1) = pairs[0], pairs[1]
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0), x < pairs[0][0]
        if x >= pairs[-1][0]:
            (x0, y0), (x1, y1) = pairs[-2], pairs[-1]
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0), x > pairs[-1][0]
        for (x0, y0), (x1, y1) in zip(pairs, pairs[1:]):
            if x0 <= x <= x1:
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0), False

    def nominal(self, pid, distance_m, angle_deg):
        """mm nominales perforables. Devuelve (mm, extrapolado) o (None, False)."""
        by_angle = self.table.get(pid)
        if not by_angle:
            return None, False
        # primero en distancia, dentro de cada angulo tabulado
        per_angle = []
        for a in sorted(by_angle):
            pairs = sorted(by_angle[a].items())
            mm, ext_d = self._interp(pairs, distance_m)
            if mm is not None:
                per_angle.append((a, mm, ext_d))
        if not per_angle:
            return None, False
        # luego en angulo
        mm, ext_a = self._interp([(a, v) for a, v, _ in per_angle], angle_deg)
        ext_d = any(e for _, _, e in per_angle)
        return mm, bool(ext_a or ext_d)

    def los(self, pid, distance_m, angle_deg):
        """Capacidad en linea de vision, que es contra lo que se compara el
        camino medido en la malla. Devuelve (mm, extrapolado)."""
        mm, ext = self.nominal(pid, distance_m, angle_deg)
        if mm is None:
            return None, False
        basis = (self.meta.get(pid) or ('', '', ''))[1] or 'nominal'
        if basis == 'los':
            return mm, ext
        return mm / math.cos(math.radians(angle_deg)), ext


RHO_RHA = 7850.0   # kg/m3


def spall_fraction(spall_material, caliber_mm, path_eq_mm, penetrating_mass_kg):
    """Reparto de la energia residual entre metralla de la placa y nucleo.

    Razon de masas: la masa arrancada a la placa frente a la del penetrador.
    m_astillado = spall * rho_RHA * (pi/4) * d^2 * camino_equivalente
    """
    m_spall = (spall_material * RHO_RHA * math.pi / 4.0
               * (caliber_mm / 1000.0) ** 2 * (path_eq_mm / 1000.0))
    return m_spall, m_spall / (m_spall + penetrating_mass_kg)


def selftest():
    import tempfile
    rows = ("shell_id,distance_m,angle_deg,penetration_mm,armour_type,"
            "angle_from,thickness_basis,criterion,source\n"
            "T,0,0,100,RHA,normal,nominal,complete,x\n"
            "T,1000,0,50,RHA,normal,nominal,complete,x\n"
            "T,0,60,80,RHA,normal,nominal,complete,x\n"
            "T,1000,60,40,RHA,normal,nominal,complete,x\n")
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, 'penetration.csv'), 'w').write(rows)
        open(os.path.join(d, 'shells.csv'), 'w').write(
            "shell_id,name,type,caliber_mm,mass_kg,muzzle_velocity_ms,"
            "explosive_mass_g,fuze_delay_ms,core_mass_g\nT,T,AP,75,6,800,0,,\n")
        open(os.path.join(d, 'materials.csv'), 'w').write(
            "id,resistance,spall,source\nRHA,1.0,0.1,x\n")
        bd = BallisticData(d)
    assert bd.nominal('T', 0, 0)[0] == 100
    assert bd.nominal('T', 500, 0)[0] == 75           # mitad de camino
    assert bd.nominal('T', 0, 30)[0] == 90            # mitad entre 100 y 80
    assert bd.nominal('T', 500, 60)[0] == 60
    # LOS: 80 mm nominales a 60 grados = 80 / cos 60 = 160
    assert abs(bd.los('T', 0, 60)[0] - 160.0) < 1e-9
    assert bd.los('T', 0, 0)[0] == 100                # a 0 grados coinciden
    assert bd.nominal('T', 2000, 0)[1] is True        # fuera de rango
    assert bd.nominal('NOEXISTE', 0, 0) == (None, False)
    # spall: mas camino -> mas metralla; mas penetrador -> menos
    _, f80 = spall_fraction(0.3, 75, 80, 6.8)
    _, f20 = spall_fraction(0.3, 75, 20, 6.8)
    assert 0 < f20 < f80 < 1
    assert spall_fraction(0.0, 75, 80, 6.8)[1] == 0.0
    print('selftest OK')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
        sys.exit()
    bd = BallisticData(sys.argv[1] if len(sys.argv) > 1 else 'data')
    print(f"{len(bd.projectiles)} proyectiles, {len(bd.materials)} materiales")
    for pid in bd.table:
        angles = sorted(bd.table[pid])
        n = sum(len(v) for v in bd.table[pid].values())
        print(f"  {pid}: {n} valores, angulos {angles}")
    if bd.warnings:
        print(f"\n{len(bd.warnings)} avisos:")
        for w in bd.warnings:
            print(f"  - {w}")

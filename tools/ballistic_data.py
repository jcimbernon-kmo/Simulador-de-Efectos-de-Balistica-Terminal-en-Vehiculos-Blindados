"""Carga las tablas de data/ (shells, penetration, velocity, materials), valida
y consulta la penetracion y la velocidad interpoladas.

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
        self.velocities = {}   # projectile_id -> [(distance_m, velocity_ms)] ordenado
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
            for k in ('caliber_mm', 'core_diameter_mm', 'mass_kg',
                      'muzzle_velocity_ms', 'explosive_mass_g', 'fuze_delay_ms',
                      'core_mass_kg', 'core_mass_g'):
                r[k] = _num(r.get(k))
            if r['core_mass_kg'] is None and r['core_mass_g'] is not None:
                r['core_mass_kg'] = r['core_mass_g'] / 1000.0
            # masa que de verdad penetra: el nucleo en APCR, el proyectil entero si no
            r['penetrating_mass_kg'] = r['core_mass_kg'] or r['mass_kg']
            # Diametro del penetrador, por el mismo criterio (§3.5): el nucleo
            # en el APCR y el calibre en el resto. caliber_mm se queda siendo
            # el calibre de verdad, que es lo que empareja con cd y con el
            # umbral de rebote de §6.
            r['penetrating_diameter_mm'] = r['core_diameter_mm'] or r['caliber_mm']
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
            if r['core_diameter_mm'] is not None and r['caliber_mm'] is not None \
                    and r['core_diameter_mm'] > r['caliber_mm']:
                self.warnings.append(
                    f"ERROR: {r['id']}: core_diameter_mm = "
                    f"{r['core_diameter_mm']} es mayor que el calibre "
                    f"({r['caliber_mm']}); un nucleo no cabe fuera del casquillo")
            if r['type'] == 'APCR' and r['core_diameter_mm'] is None:
                # El tapon va con d^2, asi que caer al calibre lo infla mucho.
                self.warnings.append(
                    f"{r['id']}: APCR sin core_diameter_mm; se usa el calibre "
                    f"({r['caliber_mm']:.0f} mm) y la masa de tapon de §3.5 "
                    f"sale sobrestimada")

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

        self._load_velocity(folder, known)

    def _load_velocity(self, folder, known):
        """velocity.csv: velocidad de impacto frente a distancia.

        Hace falta para la cadena de capas (§3.4.1), la energia residual y el
        tapon (§3.5) y el recorrido de la espoleta del APHE (§4).
        """
        seen = set()
        for r in self._rows(folder, 'velocity.csv'):
            pid = r.get('shell_id') or r.get('projectile_id')
            seen.add(pid)
            where = f" en velocity.csv ({pid}, {r.get('distance_m')} m)"
            d, v = _num(r.get('distance_m'), where), _num(r.get('velocity_ms'), where)
            if d is None or v is None:
                self.warnings.append(
                    f"{pid} {r.get('distance_m')}m: velocidad sin valor")
                continue
            if not 50.0 <= v <= 2000.0:
                self.warnings.append(
                    f"{pid} {d:.0f}m: {v} m/s es implausible; revisa el "
                    "separador decimal")
            self.velocities.setdefault(pid, []).append((d, v))

        for pid in self.velocities:
            self.velocities[pid].sort()

        for pid in sorted(seen - known):
            self.warnings.append(
                f"ERROR: velocity.csv usa '{pid}', que no esta en shells.csv")
        for pid in sorted(known - seen):
            self.warnings.append(
                f"{pid}: sin filas en velocity.csv; sin velocidad de impacto no "
                "hay energia (§3.5) ni retardo de espoleta (§4)")

        for pid, pairs in sorted(self.velocities.items()):
            # Un proyectil no acelera por el camino. Si sube, el dato esta mal.
            for (d0, v0), (d1, v1) in zip(pairs, pairs[1:]):
                if v1 > v0:
                    self.warnings.append(
                        f"ERROR: {pid}: la velocidad sube de {v0:.0f} a "
                        f"{v1:.0f} m/s entre {d0:.0f} y {d1:.0f} m")
            if len(pairs) > 1 and len({v for _, v in pairs}) == 1:
                self.warnings.append(
                    f"{pid}: velocidad constante a {pairs[0][1]:.0f} m/s en "
                    f"{len(pairs)} filas. No es una medicion: declararlo (§9)")
            boca = (self.projectiles.get(pid) or {}).get('muzzle_velocity_ms')
            en_boca = dict(pairs).get(0.0)
            if boca is not None and en_boca is not None and abs(boca - en_boca) > 1.0:
                self.warnings.append(
                    f"{pid}: muzzle_velocity_ms = {boca:.0f} en shells.csv pero "
                    f"velocity.csv da {en_boca:.0f} a 0 m")

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

    def velocity(self, pid, distance_m):
        """Velocidad de impacto en m/s. Devuelve (v, extrapolado).

        Mas alla de la ultima distancia tabulada se recorta al ultimo valor en
        vez de extrapolar: la perdida de velocidad es convexa, asi que la recta
        se iria por debajo y a 4000 m daria negativo.
        """
        pairs = self.velocities.get(pid)
        if not pairs:
            return None, False
        v, ext = self._interp(pairs, distance_m)
        if v is not None and v <= 0.0:
            return pairs[-1][1], True
        return v, ext

    def impact_energy(self, pid, distance_m):
        """Energia cinetica del penetrador al impactar, en julios (§3.5).

        Usa penetrating_mass_kg, que es el nucleo en el APCR y el proyectil
        entero en el resto. Devuelve (julios, extrapolado).
        """
        v, ext = self.velocity(pid, distance_m)
        m = (self.projectiles.get(pid) or {}).get('penetrating_mass_kg')
        if v is None or m is None:
            return None, False
        return 0.5 * m * v * v, ext

    def spall_split(self, pid, material_id, path_eq_mm):
        """(m_tapon_kg, fraccion_astillado) de §3.5 y §3.6.

        Envuelve spall_fraction() tomando el diametro y la masa del penetrador
        de las tablas, para que nadie pueda pasarle el calibre del casquillo
        donde va el diametro del nucleo. Devuelve (None, None) si falta un dato.
        """
        p = self.projectiles.get(pid)
        mat = self.materials.get(material_id) or {}
        if not p or mat.get('spall') is None \
                or p.get('penetrating_diameter_mm') is None:
            return None, None
        return spall_fraction(mat['spall'], p['penetrating_diameter_mm'],
                              path_eq_mm, p['penetrating_mass_kg'])


RHO_RHA = 7850.0   # kg/m3


def spall_fraction(spall_material, penetrator_diameter_mm, path_eq_mm,
                   penetrating_mass_kg):
    """Reparto de la energia residual entre metralla de la placa y nucleo.

    Razon de masas: la masa arrancada a la placa frente a la del penetrador.
    m_astillado = spall * rho_RHA * (pi/4) * d^2 * camino_equivalente

    El diametro es el del PENETRADOR, no el calibre: en el APCR es el nucleo
    (§3.5). Va al cuadrado, asi que confundirlos en el PzGr. 40 multiplica la
    masa de tapon por (75/28)^2 = 7,2. Usa BallisticData.spall_split(), que
    coge el diametro correcto de las tablas.
    """
    m_spall = (spall_material * RHO_RHA * math.pi / 4.0
               * (penetrator_diameter_mm / 1000.0) ** 2 * (path_eq_mm / 1000.0))
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
        open(os.path.join(d, 'velocity.csv'), 'w').write(
            "shell_id,distance_m,velocity_ms\n"
            "T,0,800\nT,1000,600\nT,2000,400\n")
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

    # --- velocidad ---
    assert bd.velocity('T', 0) == (800.0, False)          # punto tabulado
    assert bd.velocity('T', 500) == (700.0, False)        # interpolado
    assert bd.velocity('T', 2000) == (400.0, False)
    assert bd.velocity('T', 2500)[1] is True              # extrapolado
    assert bd.velocity('T', 9000) == (400.0, True)        # recortado, no negativo
    assert bd.velocity('NOEXISTE', 0) == (None, False)

    # energia: 1/2 * 6 kg * 800^2 = 1,92 MJ
    e, ext = bd.impact_energy('T', 0)
    assert abs(e - 0.5 * 6.0 * 800.0 ** 2) < 1e-6 and ext is False
    # a mas distancia, menos energia
    assert bd.impact_energy('T', 1000)[0] < e
    assert bd.impact_energy('NOEXISTE', 0) == (None, False)
    # el caso bueno no genera avisos de velocidad
    assert not [w for w in bd.warnings if 'velocity.csv' in w or 'm/s' in w]

    # --- validacion: una velocidad que sube es un error de datos ---
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, 'penetration.csv'), 'w').write(rows)
        open(os.path.join(d, 'shells.csv'), 'w').write(
            "shell_id,name,type,caliber_mm,mass_kg,muzzle_velocity_ms,"
            "explosive_mass_g,fuze_delay_ms,core_mass_g\nT,T,AP,75,6,800,0,,\n")
        open(os.path.join(d, 'materials.csv'), 'w').write(
            "id,resistance,spall,source\nRHA,1.0,0.1,x\n")
        open(os.path.join(d, 'velocity.csv'), 'w').write(
            "shell_id,distance_m,velocity_ms\n"
            "T,0,600\nT,1000,700\n")       # acelera, y no cuadra con la boca
        mal = BallisticData(d)
    assert any('la velocidad sube' in w for w in mal.warnings), mal.warnings
    assert any('muzzle_velocity_ms' in w for w in mal.warnings), mal.warnings

    # --- validacion: velocidad constante se avisa, no se acepta en silencio ---
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, 'penetration.csv'), 'w').write(rows)
        open(os.path.join(d, 'shells.csv'), 'w').write(
            "shell_id,name,type,caliber_mm,mass_kg,muzzle_velocity_ms,"
            "explosive_mass_g,fuze_delay_ms,core_mass_g\nT,T,HEAT,75,5,450,600,0,\n")
        open(os.path.join(d, 'materials.csv'), 'w').write(
            "id,resistance,spall,source\nRHA,1.0,0.1,x\n")
        open(os.path.join(d, 'velocity.csv'), 'w').write(
            "shell_id,distance_m,velocity_ms\nT,0,450\nT,1000,450\nT,2000,450\n")
        cte = BallisticData(d)
    assert any('velocidad constante' in w for w in cte.warnings), cte.warnings

    # --- diametro del penetrador ---
    # Sin columna: cae al calibre, y la tabla antigua sigue cargando.
    assert bd.projectiles['T']['penetrating_diameter_mm'] == 75.0
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, 'penetration.csv'), 'w').write(
            rows + "A,0,0,170,RHA,normal,nominal,complete,x\n")
        open(os.path.join(d, 'shells.csv'), 'w').write(
            "shell_id,name,type,caliber_mm,core_diameter_mm,mass_kg,"
            "muzzle_velocity_ms,explosive_mass_g,fuze_delay_ms,core_mass_kg\n"
            "T,T,AP,75,,6,800,0,,\n"
            "A,A,APCR,75,28,4.1,930,0,,0.85\n"
            "X,X,APCR,75,99,4.1,930,0,,0.85\n")       # nucleo mas ancho que el obus
        open(os.path.join(d, 'materials.csv'), 'w').write(
            "id,resistance,spall,source\nRHA,1.0,1.0,x\n")
        open(os.path.join(d, 'velocity.csv'), 'w').write(
            "shell_id,distance_m,velocity_ms\n"
            "T,0,800\nA,0,930\nX,0,930\n")
        ap = BallisticData(d)
    # El APCR usa el nucleo; el calibre se queda intacto para cd y el rebote.
    assert ap.projectiles['A']['penetrating_diameter_mm'] == 28.0
    assert ap.projectiles['A']['caliber_mm'] == 75.0
    assert ap.projectiles['A']['penetrating_mass_kg'] == 0.85
    assert any('core_diameter_mm' in w and 'mayor que el calibre' in w
               for w in ap.warnings), ap.warnings

    # spall_split coge el diametro bueno: 28 mm da mucho menos tapon que 75
    m28, f28 = ap.spall_split('A', 'RHA', 80.0)
    m75, f75 = spall_fraction(1.0, 75.0, 80.0, 0.85)
    assert abs(m75 / m28 - (75.0 / 28.0) ** 2) < 1e-9
    assert f28 < f75
    assert ap.spall_split('A', 'NOEXISTE', 80.0) == (None, None)
    assert ap.spall_split('NOEXISTE', 'RHA', 80.0) == (None, None)

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

    print("\nVelocidad y energia de impacto del penetrador:")
    print(f"  {'proyectil':16s}" + ''.join(f"{d:>14d} m" for d in (0, 500, 1000, 2000)))
    for pid in sorted(bd.velocities):
        celdas = ''
        for d in (0, 500, 1000, 2000):
            v, _ = bd.velocity(pid, d)
            e, _ = bd.impact_energy(pid, d)
            celdas += f"  {v:4.0f} m/s {e / 1e6:5.3f} MJ" if v is not None else f"{'-':>16s}"
        print(f"  {pid:16s}{celdas}")
    if bd.warnings:
        print(f"\n{len(bd.warnings)} avisos:")
        for w in bd.warnings:
            print(f"  - {w}")

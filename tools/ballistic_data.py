#Carga las tablas de data/ (shells, penetration, velocity, materials) e interpola la penetracion y la velocidad. Solo datos: la fisica esta en disparo.py.

import csv
import math
import os
import sys

NUMERICOS = ('caliber_mm', 'core_diameter_mm', 'mass_kg', 'muzzle_velocity_ms', 'explosive_mass_g', 'fuze_delay_ms', 'core_mass_kg', 'cd')

def _num(s):
    #Transformar decimales (, -> .)
    raw = (s or '').strip()
    return float(raw.replace(',', '.')) if raw else None

def _filas(folder, nombre):
    with open(os.path.join(folder, nombre), newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

class BallisticData:
    def __init__(self, folder):
        self.projectiles = {}
        for r in _filas(folder, 'shells.csv'):
            for k in NUMERICOS:
                r[k] = _num(r.get(k))
            if r['type'] == 'APCR' and (r['core_mass_kg'] is None or r['core_diameter_mm'] is None):
                raise ValueError(f"{r['shell_id']}: APCR sin core_mass_kg o core_diameter_mm")
            #El nucleo en el APCR/sabot, el proyectil entero en el resto.
            r['penetrating_mass_kg'] = r['core_mass_kg'] or r['mass_kg']
            r['penetrating_diameter_mm'] = r['core_diameter_mm'] or r['caliber_mm']
            self.projectiles[r['shell_id']] = r

        self.materials = {}
        for r in _filas(folder, 'materials.csv'):
            r['resistance'], r['spall'] = _num(r['resistance']), _num(r['spall'])
            self.materials[r['id']] = r

        self.table = {}        #shell_id -> {angulo: {distancia: mm}}
        self.basis = {}        #shell_id -> 'nominal' o 'los'
        for r in _filas(folder, 'penetration.csv'):
            mm = _num(r['penetration_mm'])
            if mm is None:
                continue
            pid = r['shell_id']
            self.table.setdefault(pid, {}).setdefault(_num(r['angle_deg']), {})[_num(r['distance_m'])] = mm
            self.basis[pid] = (r.get('thickness_basis') or '').strip() or 'nominal'

        self.velocities = {}   # shell_id -> [(distancia_m, velocidad_ms)] ordenado
        for r in _filas(folder, 'velocity.csv'):
            d, v = _num(r['distance_m']), _num(r['velocity_ms'])
            if d is not None and v is not None:
                self.velocities.setdefault(r['shell_id'], []).append((d, v))
        for pares in self.velocities.values():
            pares.sort()

    @staticmethod
    def _interp(pares, x):
        """Interpola en [(x, y)] ordenada, extrapolando con el tramo extremo.
        Devuelve (y, extrapolado)."""
        if not pares:
            return None, False
        if len(pares) == 1:
            return pares[0][1], x != pares[0][0]
        i = 1
        while i < len(pares) - 1 and x > pares[i][0]:
            i += 1
        (x0, y0), (x1, y1) = pares[i - 1], pares[i]
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0), not pares[0][0] <= x <= pares[-1][0]

    def nominal(self, pid, distance_m, angle_deg):
        """mm nominales perforables: primero en distancia, luego en angulo.
        Devuelve (mm, extrapolado) o (None, False)."""
        por_angulo = self.table.get(pid)
        if not por_angulo:
            return None, False
        filas = [(a, *self._interp(sorted(por_angulo[a].items()), distance_m))
                 for a in sorted(por_angulo)]
        mm, ext = self._interp([(a, v) for a, v, _ in filas], angle_deg)
        return mm, ext or any(e for _, _, e in filas)

    def los(self, pid, distance_m, angle_deg):
        """Capacidad en linea de vision, que es contra lo que se compara el camino
        medido en la malla. Devuelve (mm, extrapolado)."""
        mm, ext = self.nominal(pid, distance_m, angle_deg)
        if mm is None or self.basis.get(pid) == 'los':
            return mm, ext
        return mm / math.cos(math.radians(angle_deg)), ext

    def velocity(self, pid, distance_m):
        """Velocidad de impacto. Devuelve (v, extrapolado). Pasada la tabla se
        recorta al ultimo valor: la recta llegaria a dar velocidades negativas."""
        pares = self.velocities.get(pid)
        v, ext = self._interp(pares, distance_m)
        if v is not None and v <= 0.0:
            return pares[-1][1], True
        return v, ext

    def exponente(self, pid, distance_m):
        """Exponente de De Marre, P proporcional a v^n, medido en las tablas del propio
        proyectil: tramo a 0 grados que contiene distance_m (fuera de rango, el tramo
        extremo). Error si no hay dos distancias con penetracion y velocidad, o si la
        velocidad o la penetracion no cambian en el tramo."""
        filas = sorted((d, mm) for d, mm in (self.table.get(pid) or {}).get(0.0, {}).items()
                       if self.velocity(pid, d)[0] is not None)
        if len(filas) < 2:
            raise ValueError(f"{pid}: el exponente de De Marre necesita dos distancias con "
                             f"penetracion a 0 grados y velocidad")
        i = 1
        while i < len(filas) - 1 and distance_m > filas[i][0]:
            i += 1
        (d0, p0), (d1, p1) = filas[i - 1], filas[i]
        v0, v1 = self.velocity(pid, d0)[0], self.velocity(pid, d1)[0]
        if v0 == v1 or p0 == p1:
            raise ValueError(f"{pid}: entre {d0:g} y {d1:g} m no cambia la velocidad o la "
                             f"penetracion; no se puede medir el exponente de De Marre")
        return math.log(p0 / p1) / math.log(v0 / v1)

    def impact_energy(self, pid, distance_m):
        """Energia cinetica del penetrador al impactar (§3.5). Devuelve (J, extrapolado)."""
        v, ext = self.velocity(pid, distance_m)
        m = (self.projectiles.get(pid) or {}).get('penetrating_mass_kg')
        if v is None or m is None:
            return None, False
        return 0.5 * m * v * v, ext


def selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        def w(nombre, texto):
            open(os.path.join(d, nombre), 'w').write(texto)
        w('shells.csv', "shell_id,name,type,caliber_mm,core_diameter_mm,mass_kg,muzzle_velocity_ms,"
                        "explosive_mass_g,fuze_delay_ms,core_mass_kg,cd\n"
                        "T,T,AP,75,,6,800,0,,,0.4\nA,A,APCR,75,28,4.1,930,0,,0.85,0.6\n")
        w('materials.csv', "id,resistance,spall\nRHA,1.0,1.0\n")
        w('penetration.csv', "shell_id,distance_m,angle_deg,penetration_mm,armour_type,"
                             "angle_from,thickness_basis,criterion\n"
                             "T,0,0,100,RHA,normal,nominal,complete\nT,1000,0,50,RHA,normal,nominal,complete\n"
                             "T,0,60,80,RHA,normal,nominal,complete\nT,1000,60,40,RHA,normal,nominal,complete\n")
        w('velocity.csv', "shell_id,distance_m,velocity_ms\nT,0,800\nT,1000,600\nT,2000,400\n")
        bd = BallisticData(d)
        w('penetration.csv', "shell_id,distance_m,angle_deg,penetration_mm,armour_type,"
                             "angle_from,thickness_basis,criterion\n"
                             "T,0,0,100,RHA,normal,nominal,complete\nT,1000,0,100,RHA,normal,nominal,complete\n")
        plano = BallisticData(d)                         # penetracion constante en el tramo
        w('shells.csv', "shell_id,name,type,caliber_mm,core_diameter_mm,mass_kg,muzzle_velocity_ms,"
                        "explosive_mass_g,fuze_delay_ms,core_mass_kg,cd\nX,X,APCR,75,,4.1,930,0,,,0.6\n")
        try:
            BallisticData(d)
            raise AssertionError('un APCR sin nucleo tiene que fallar')
        except ValueError:
            pass

    #Interpolacion en distancia, en angulo, y en las dos a la vez.
    assert bd.nominal('T', 0, 0) == (100.0, False)
    assert bd.nominal('T', 500, 0)[0] == 75.0
    assert bd.nominal('T', 0, 30)[0] == 90.0
    assert bd.nominal('T', 500, 60)[0] == 60.0
    assert bd.nominal('T', 2000, 0) == (0.0, True)
    assert bd.nominal('NOEXISTE', 0, 0) == (None, False)
    #LOS: 80 mm nominales a 60 grados son 160 mm de camino.
    assert abs(bd.los('T', 0, 60)[0] - 160.0) < 1e-9
    #Velocidad tabulada, interpolada, extrapolada y recortada.
    assert bd.velocity('T', 500) == (700.0, False)
    assert bd.velocity('T', 2500)[1] is True
    assert bd.velocity('T', 9000) == (400.0, True)
    assert bd.velocity('NOEXISTE', 0) == (None, False)
    assert abs(bd.impact_energy('T', 0)[0] - 0.5 * 6.0 * 800.0 ** 2) < 1e-6
    #APCR penetra el nucleo
    a = bd.projectiles['A']
    assert (a['penetrating_mass_kg'], a['penetrating_diameter_mm'], a['caliber_mm']) == (0.85, 28.0, 75.0)
    assert bd.projectiles['T']['penetrating_diameter_mm'] == 75.0
    #Exponente de De Marre por tramo: 100 -> 50 mm mientras v pasa de 800 a 600 m/s.
    n = math.log(100 / 50) / math.log(800 / 600)
    assert abs(bd.exponente('T', 500) - n) < 1e-12
    assert abs(bd.exponente('T', 5000) - n) < 1e-12      # fuera de rango: tramo extremo
    for pid, datos in (('A', bd), ('T', plano)):         # sin tabla / tramo sin cambio
        try:
            datos.exponente(pid, 500)
            raise AssertionError(f'{pid}: el exponente tenia que fallar')
        except ValueError:
            pass
    print('selftest OK')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
        sys.exit()
    bd = BallisticData(sys.argv[1] if len(sys.argv) > 1 else 'data')
    print(f"{len(bd.projectiles)} proyectiles, {len(bd.materials)} materiales")
    for pid, por_angulo in bd.table.items():
        print(f"  {pid}: {sum(len(v) for v in por_angulo.values())} valores, "
              f"angulos {sorted(por_angulo)}")
    print("\nExponente de De Marre por tramo de distancia (P proporcional a v^n):")
    for pid, por_angulo in bd.table.items():
        ds = sorted(por_angulo.get(0.0, {}))
        try:
            print(f"  {pid:16s}" + '  '.join(f"{a:g}-{b:g} m: {bd.exponente(pid, (a + b) / 2):.3f}"
                                         for a, b in zip(ds, ds[1:])))
        except ValueError as e:
            print(f"  {pid:16s}no aplica ({e})")
    print("\nVelocidad y energia de impacto del penetrador:")
    print(f"  {'proyectil':16s}" + ''.join(f"{d:>14d} m" for d in (0, 500, 1000, 2000)))
    for pid in sorted(bd.velocities):
        celdas = ''
        for d in (0, 500, 1000, 2000):
            v, _ = bd.velocity(pid, d)
            e, _ = bd.impact_energy(pid, d)
            celdas += f"  {v:4.0f} m/s {e / 1e6:5.3f} MJ"
        print(f"  {pid:16s}{celdas}")

#Simulacion de disparo mediante rayos, se usa el .glb, con tramos, capas por contacto, perforacion por capacidad, energia residual, perdida de energia y daño a modulos, fragmentos del tapon, y estado final.
#Lo vuelca en una linea temporal en JSON

#Falta rebote, explosivos y tipo HEAT

"""
python tools/disparo.py disparo de prueba, resumen
python tools/disparo.py --shell PzGr40_75_L48 --distance 500 --origin 0.3 -2 1.1
python tools/disparo.py --out disparo.json   ademas guarda la linea temporal
python tools/disparo.py --selftest
"""
import argparse
import csv
import json
import math
import os
import random
import sys

import ballistic_data as B
import validate_glb as V

# §3.7.1: que significa Health segun el tipo de modulo.
ACUMULATIVO = ('Engine', 'Transmission', 'Gun')   #En Julios
UMBRAL = ('Crew', 'Track', 'Ammo', 'Fuel')
CINETICOS = ('AP', 'APCBC', 'APCBC-HE', 'APCR')

#Disparo a casco frontal derecho, 100m
SHELL, DISTANCIA = 'PzGr39_75_L48', 100.0
ORIGEN, DIRECCION = (0.50, -2.00, 1.30), (0.0, 1.0, 0.0)

#Cargar datos
def cargar_parametros(folder):
    path = os.path.join(folder, 'parametros.csv')
    if not os.path.exists(path):
        raise FileNotFoundError(f"falta {path} (contact_gap_mm, rho_acero)")
    with open(path, newline='', encoding='utf-8') as f:
        par = {r['key'].strip(): B._num(r['value']) for r in csv.DictReader(f)}
    for k in ('contact_gap_mm', 'rho_acero'):
        if par.get(k) is None:
            raise ValueError(f"{path}: falta la clave '{k}'")
    return par

def sigma_rha(bd, pid, area_m2):
    #E_impacto / (espesor perforado a 100 m y 0 grados x area)
    e100, _ = bd.impact_energy(pid, 100.0)
    t100, _ = bd.nominal(pid, 100.0, 0.0)
    if e100 is None or t100 is None:
        raise ValueError(f"{pid} sin penetracion")
    return e100 / (t100 / 1000.0 * area_m2)

def cadena(cap_mm, t_mm, q):
    """§3.4.1: capacidad que queda tras una capa de t_mm de RHA equivalente."""
    return max(cap_mm ** q - t_mm ** q, 0.0) ** (1.0 / q)


#Geometria
def _normal(tri, d, contra_el_rayo):
    n = V.norm(V.cross(V.sub(tri[1], tri[0]), V.sub(tri[2], tri[0])))
    if (V.dot(n, d) > 0) == contra_el_rayo:
        n = (-n[0], -n[1], -n[2])
    return n

def trazar(objs, o, d):
    """§3.1: tramos que cruza el rayo, ordenados por entrada. Entrada = primera
    interseccion, salida = ultima (vale porque cada objeto es convexo)."""
    out = []
    for name, tris, props in objs:
        hits = []
        for tri in tris:
            t = V.ray_tri(o, d, tri)
            if t is not None and t > 1e-9:
                hits.append((t, tri))
        if len(hits) < 2:
            continue
        hits.sort(key=lambda h: h[0])
        (t_in, tri_in), (t_out, tri_out) = hits[0], hits[-1]
        if t_out - t_in < 1e-7:
            continue
        n_in = _normal(tri_in, d, True)
        out.append({'name': name, 'props': props, 't_in': t_in, 't_out': t_out,
                    'path': t_out - t_in, 'n_in': n_in,
                    'n_out': _normal(tri_out, d, False),
                    'angle': math.degrees(math.acos(min(1.0, abs(V.dot(n_in, d)))))})
    out.sort(key=lambda tr: (tr['t_in'], tr['t_out']))
    return out

def agrupar(tramos, d, contacto_m):
    capas, actual, fin = [], [], 0.0
    for tr in tramos:
        if actual and (tr['t_in'] - fin) * abs(V.dot(tr['n_in'], d)) < contacto_m:
            actual.append(tr)
            fin = max(fin, tr['t_out'])
            continue
        if actual:
            capas.append(actual)
        actual, fin = [tr], tr['t_out']
    if actual:
        capas.append(actual)
    return capas

def _punto(o, d, s):
    return tuple(o[i] + d[i] * s for i in range(3))

#Disparo
class Linea:
    #Lista de eventos con reloj: t += camino / velocidad media

    def __init__(self, s0, v0, t0=0.0, ray_id=0, parent_id=None):
        self.ev, self.t, self.s, self.v = [], t0, s0, v0
        self.ray_id, self.parent_id = ray_id, parent_id

    def avanzar(self, s, v):
        if s > self.s:
            self.t += (s - self.s) / max(0.5 * (self.v + v), 1.0)
            self.s = s
        self.v = v

    def add(self, tipo, tr, pos, normal, **campos):
        e = {'type': tipo, 't_s': round(self.t, 9), 'ray_id': self.ray_id,
             'parent_id': self.parent_id,
             'object': tr['name'] if tr else None,
             'pos': [round(x, 5) for x in pos], 'normal': [round(x, 5) for x in normal]}
        for k, v in campos.items():
            e[k] = round(v, 4) if isinstance(v, float) else v
        self.ev.append(e)

def disparar(objs, bd, par, pid, distancia_m, origen, direccion):
    d = V.norm(direccion)
    p = bd.projectiles[pid]
    if p['type'] not in CINETICOS:
        raise ValueError(f"{pid}: tipo {p['type']} no soportado (solo {CINETICOS})")
    m, dmm = p['penetrating_mass_kg'], p['penetrating_diameter_mm']
    area = math.pi / 4.0 * (dmm / 1000.0) ** 2
    n = bd.exponente(pid, distancia_m)   #De Marre medido en las tablas de este proyectil
    q = 2.0 / n
    v0, _ = bd.velocity(pid, distancia_m)
    E = 0.5 * m * v0 * v0
    sigma = sigma_rha(bd, pid, area)
    cono = par.get(f"cono_fragmentos_{p['type']}_deg")   #Semiangulo del cono segun el tipo
    if cono is None:
        raise ValueError(f"parametros.csv: falta la clave 'cono_fragmentos_{p['type']}_deg' (§3.6)")
    salud0 = {nm: float(pr['Health']) for nm, _, pr in objs if 'Module_Type' in pr}
    eventos_fragmentos, ids = [], [0]
    aviso = []
    if p['type'] == 'APCBC-HE':
        aviso.append(f"{pid}: la carga de {p['explosive_mass_g']} g y la espoleta de "
                     f"{p['fuze_delay_ms']} ms no se simulan todavia (§4)")

    def res(tr):
        r = (bd.materials.get(tr['props'].get('Armour_Material')) or {}).get('resistance')
        if r is None:
            raise ValueError(f"{tr['name']}: material sin resistance")
        return r

    def eq_mm(tr): #RHA equivalente del tramo
        return tr['path'] * 1000.0 * res(tr)

    todos = trazar(objs, origen, d)
    sin_material = [t['name'] for t in todos if 'Armour_Material' not in t['props']]
    if sin_material:
        aviso.append(f"objetos sin Armour_Material, ignorados: {sin_material}")
    tramos = [t for t in todos if 'Armour_Material' in t['props']]
    meta = {'shell': pid, 'distance_m': distancia_m, 'origin': list(origen),
            'direction': [round(x, 6) for x in d], 'impact_velocity_ms': round(v0, 3),
            'impact_energy_J': round(E, 3), 'sigma_RHA_GPa': round(sigma / 1e9, 4),
            'n_de_marre': n, 'penetrating_mass_kg': m, 'penetrating_diameter_mm': dmm}
    if not tramos:
        meta['warnings'] = aviso + ['el rayo no toca nada']
        return {'meta': meta, 'events': [], 'layers': [], 'final_state': {}}

    capas = agrupar(tramos, d, par['contact_gap_mm'] / 1000.0)
    P0, ext = bd.los(pid, distancia_m, tramos[0]['angle'])
    if P0 is None:
        raise ValueError(f"{pid}: sin tabla de penetracion")
    if ext:
        aviso.append(f"capacidad extrapolada fuera de la tabla "
                     f"({tramos[0]['angle']:.1f} grados a {distancia_m:.0f} m)")
    P0 = max(P0, 0.0)
    meta['first_layer_capacity_mm'] = round(P0, 3)
    E0 = E
    semilla = f"{pid}|{distancia_m}|{tuple(round(x, 6) for x in origen)}|{tuple(round(x, 6) for x in d)}"
    lin = Linea(tramos[0]['t_in'], v0)
    parado, fantasma = False, False
    resumen_capas = []

    def energia_a_v(e):
        return math.sqrt(max(2.0 * e / m, 0.0))

    def golpe_modulo(tr, e_in, cap_in, cap_out, deposita_todo=False, prof_m=None):
        """§3.7 / §3.7.1 sobre un tramo de modulo. Devuelve la energia que sale."""
        nonlocal fantasma
        tipo = tr['props']['Module_Type']
        if deposita_todo:
            e_out = 0.0
        else:
            e_out = e_in * (cap_out / cap_in) ** q if cap_in > 0 else 0.0
        if e_out <= 0.0 and cap_out > 0.0 and not fantasma and not deposita_todo:
            # Con una sola cuenta esto no puede pasar: energia y capacidad estan
            # ligadas por P = P0*(E/E0)^(n/2) y se agotan juntas.
            fantasma = True
            aviso.append(f"{tr['name']}: el nucleo se queda sin energia con {cap_out:.1f} mm "
                         f"de capacidad, lo que con una sola cuenta no deberia ocurrir")
        #Health, health_in/out y out_of_service los pone aplicar_salud() al final, en orden de tiempo, porque nucleo y fragmentos pueden tocar el mismo modulo.
        tipo_ev = 'detonation' if (tipo == 'Ammo' and e_in >= salud0[tr['name']]) else 'module_hit'
        lin.add(tipo_ev, tr, _punto(origen, d, tr['t_in']), tr['n_in'],
                path_mm=(tr['path'] if prof_m is None else prof_m) * 1000.0,
                angle_deg=tr['angle'], capacity_in_mm=cap_in, capacity_out_mm=cap_out,
                energy_in_J=e_in, energy_out_J=e_out)
        return e_out

    for capa in capas:
        T = sum(eq_mm(tr) for tr in capa)
        cap_in = P0 * (E / E0) ** (n / 2.0)
        resumen_capas.append({'objects': [tr['name'] for tr in capa],
                              'path_mm': round(sum(tr['path'] for tr in capa) * 1000, 3),
                              'equivalent_mm': round(T, 3)})

        def cap_tras(acum):
            return cadena(cap_in, acum, q)

        lin.avanzar(capa[0]['t_in'], energia_a_v(E))
        acum = 0.0
        if T > cap_in + 1e-9:                             # §3.4.2: se queda clavado
            if 'Module_Type' not in capa[0]['props']:
                lin.add('impact', capa[0], _punto(origen, d, capa[0]['t_in']), capa[0]['n_in'],
                        path_mm=capa[0]['path'] * 1000.0, angle_deg=capa[0]['angle'],
                        capacity_in_mm=cap_in, energy_in_J=E)
            for tr in capa:
                e = eq_mm(tr)
                es_mod = 'Module_Type' in tr['props']
                if acum + e > cap_in + 1e-9:
                    r = res(tr)
                    prof_m = (cap_in - acum) / r / 1000.0 if r > 0 else tr['path']
                    lin.avanzar(tr['t_in'] + prof_m, 0.0)
                    pos = _punto(origen, d, tr['t_in'] + prof_m)
                    if es_mod:
                        golpe_modulo(tr, E, cap_tras(acum), 0.0, True, prof_m)
                    lin.add('stopped', tr, pos, tr['n_in'], path_mm=prof_m * 1000.0,
                            angle_deg=tr['angle'], capacity_in_mm=cap_tras(acum),
                            capacity_out_mm=0.0, energy_in_J=E, energy_out_J=0.0)
                    E, parado = 0.0, True
                    break
                if es_mod:
                    E = golpe_modulo(tr, E, cap_tras(acum), cap_tras(acum + e))
                    lin.avanzar(tr['t_out'], energia_a_v(E))
                acum += e
            if parado:
                break
            continue

        i = 0 #La capa se perfora
        while i < len(capa):
            tr = capa[i]
            if 'Module_Type' in tr['props']:
                e = eq_mm(tr)
                E = golpe_modulo(tr, E, cap_tras(acum), cap_tras(acum + e))
                lin.avanzar(tr['t_out'], energia_a_v(E))
                acum += e
                i += 1
                continue
            paq = [] #Sobre placas contiguas
            while i < len(capa) and 'Module_Type' not in capa[i]['props']:
                paq.append(capa[i])
                i += 1
            Tp = sum(eq_mm(t) for t in paq)
            cap_a, cap_b = cap_tras(acum), cap_tras(acum + Tp)
            lin.add('impact', paq[0], _punto(origen, d, paq[0]['t_in']), paq[0]['n_in'],
                    path_mm=sum(t['path'] for t in paq) * 1000.0, angle_deg=paq[0]['angle'],
                    capacity_in_mm=cap_a, energy_in_J=E)
            v_i = energia_a_v(E)
            v_bl = v0 * (Tp / P0) ** (1.0 / n) if P0 > 0 else v_i
            m_tap = 0.0 #Tapon con el diametro del penetrador.
            for t in paq:
                sp = (bd.materials.get(t['props']['Armour_Material']) or {}).get('spall')
                if sp is None:
                    raise ValueError(f"{t['name']}: material sin spall")
                m_tap += sp * par['rho_acero'] * area * t['path']
            a = m / (m + m_tap)
            vr2 = a * (v_i ** 2 - v_bl ** 2)
            if vr2 < 0:
                aviso.append(f"{paq[0]['name']}: la capacidad ({cap_a:.1f} mm) dice que "
                             f"perfora pero la energia no (v={v_i:.0f} m/s < v_limite="
                             f"{v_bl:.0f} m/s); el nucleo sale sin energia")
                vr2 = 0.0
            e_nucleo, e_tapon = 0.5 * m * vr2, 0.5 * m_tap * vr2
            e_cizalla = E - e_nucleo - e_tapon
            ultima = paq[-1]
            cap_b = P0 * (e_nucleo / E0) ** (n / 2.0) #La capacidad sigue a la energia
            lin.avanzar(ultima['t_out'], math.sqrt(vr2))
            lin.add('perforation', ultima, _punto(origen, d, ultima['t_out']), ultima['n_out'],
                    path_mm=sum(t['path'] for t in paq) * 1000.0, angle_deg=paq[0]['angle'],
                    capacity_in_mm=cap_a, capacity_out_mm=cap_b,
                    energy_in_J=E, energy_out_J=e_nucleo,
                    plug_mass_kg=m_tap, spall_energy_J=e_tapon, shear_energy_J=e_cizalla)
            if m_tap > 0.0 and e_tapon > 0.0: #El tapon se rompe
                eventos_fragmentos.extend(fragmentos(
                    objs, bd, par, _punto(origen, d, ultima['t_out']), d, lin.t,
                    m_tap, e_tapon, ultima, semilla, ids, cono))
            E, acum = e_nucleo, acum + Tp

    if not parado:
        ult = tramos[-1]
        lin.avanzar(ult['t_out'], energia_a_v(E))
        cap_fin = P0 * (E / E0) ** (n / 2.0)
        lin.add('exit', ult, _punto(origen, d, ult['t_out']), ult['n_out'],
                capacity_in_mm=cap_fin, capacity_out_mm=cap_fin, energy_in_J=E, energy_out_J=E)
    meta['warnings'] = aviso
    eventos = sorted(lin.ev + eventos_fragmentos, key=lambda e: e['t_s'])   # estable
    salud = aplicar_salud(salud0, objs, eventos)
    return {'meta': meta, 'events': eventos, 'layers': resumen_capas,
            'final_state': estado_final(objs, salud, eventos)}


def aplicar_salud(salud0, objs, eventos):
    """§3.7.1 en orden de tiempo: acumulativos restan lo depositado (por el peso
    del rayo), umbrales comparan la energia de entrada y no se tocan."""
    tipo = {nm: pr['Module_Type'] for nm, _, pr in objs if 'Module_Type' in pr}
    salud = dict(salud0)
    for e in eventos:
        if e['type'] not in ('module_hit', 'detonation'):
            continue
        nm, h_in = e['object'], salud[e['object']]
        if tipo[nm] in ACUMULATIVO:
            h_out = max(0.0, h_in - (e['energy_in_J'] - e['energy_out_J']))
            fuera = h_out <= 0.0
        else:
            h_out, fuera = h_in, e['energy_in_J'] >= h_in
        salud[nm] = h_out
        e.update(health_in_J=round(h_in, 4), health_out_J=round(h_out, 4), out_of_service=fuera)
    return salud


def _cono(d, semi_rad, rng):
    """Direccion al azar, uniforme en angulo solido, dentro del cono alrededor de d."""
    a = (1.0, 0.0, 0.0) if abs(d[0]) < 0.9 else (0.0, 1.0, 0.0)
    e1 = V.norm(V.cross(d, a))
    e2 = V.cross(d, e1)
    c = 1.0 - rng.random() * (1.0 - math.cos(semi_rad))
    s, phi = math.sqrt(max(0.0, 1.0 - c * c)), 2.0 * math.pi * rng.random()
    return V.norm(tuple(d[i] * c + (e1[i] * math.cos(phi) + e2[i] * math.sin(phi)) * s
                        for i in range(3)))


def fragmentos(objs, bd, par, p0, d, t0, m_tap, e_tapon, placa, semilla, ids, cono_deg):
    """§3.6: el tapon se rompe en N fragmentos iguales que salen a la velocidad del
    nucleo dentro de un cono, repartiendose e_tapon. Cada fragmento es un rayo que
    pierde E por recorrido (§3.7) y dana modulos con las reglas de §3.7.1.
    Sin fragmentos secundarios, sin rebote y sin rotura del proyectil (§9)."""
    for k in ('masa_fragmento_g', 'sigma_fragmento_GPa', 'rho_acero',
              'energia_minima_fragmento_J'):
        if par.get(k) is None:
            raise ValueError(f"parametros.csv: falta la clave '{k}' (§3.6)")
    n_frag = max(1, round(m_tap / (par['masa_fragmento_g'] / 1000.0)))
    m_f, e_f = m_tap / n_frag, e_tapon / n_frag            # suma exacta: presupuesto de §1
    d_f = (6.0 * m_f / (math.pi * par['rho_acero'])) ** (1.0 / 3.0)   # esfera de acero
    k_perdida = par['sigma_fragmento_GPa'] * 1e9 * math.pi / 4.0 * d_f * d_f   # J por m de RHA
    rng = random.Random(f"{semilla}|{placa['name']}")
    padre = 0
    spawn = Linea(0.0, 0.0, t0, padre, None)
    spawn.add('fragment_spawn', placa, p0, placa['n_out'], n_fragments=n_frag,
              fragment_mass_kg=m_f, fragment_diameter_mm=d_f * 1000.0,
              energy_in_J=e_tapon, energy_out_J=e_tapon)
    ev = spawn.ev
    #Un rayo por fragmento, unos 5 ms por rayo en Python Si un barrido lo necesita: rayos representativos con peso.
    for _ in range(n_frag):
        ids[0] += 1
        u = _cono(d, math.radians(cono_deg), rng)
        o = tuple(p0[i] + u[i] * 1e-5 for i in range(3))
        E = e_f
        lin = Linea(0.0, math.sqrt(2.0 * E / m_f), t0, ids[0], padre)
        ultimo, parado = None, False
        for tr in trazar(objs, o, u):
            r = (bd.materials.get(tr['props'].get('Armour_Material')) or {}).get('resistance')
            if r is None:
                continue                                  # sin material: no frena
            lin.avanzar(tr['t_in'], math.sqrt(2.0 * E / m_f))
            perdida = tr['path'] * r * k_perdida
            es_mod = 'Module_Type' in tr['props']
            if E - perdida < par['energia_minima_fragmento_J']:   # se queda dentro
                prof = min(E / (r * k_perdida), tr['path']) if r > 0 else tr['path']
                if es_mod:
                    lin.add('module_hit', tr, _punto(o, u, tr['t_in']), tr['n_in'],
                            path_mm=prof * 1000.0, angle_deg=tr['angle'],
                            energy_in_J=E, energy_out_J=0.0)
                lin.avanzar(tr['t_in'] + prof, 0.0)
                lin.add('stopped', tr, _punto(o, u, tr['t_in'] + prof), tr['n_in'],
                        path_mm=prof * 1000.0, angle_deg=tr['angle'],
                        energy_in_J=E, energy_out_J=0.0)
                parado = True
                break
            if es_mod:
                tipo = 'detonation' if (tr['props']['Module_Type'] == 'Ammo' and
                                        E >= float(tr['props']['Health'])) else 'module_hit'
                lin.add(tipo, tr, _punto(o, u, tr['t_in']), tr['n_in'],
                        path_mm=tr['path'] * 1000.0, angle_deg=tr['angle'],
                        energy_in_J=E, energy_out_J=E - perdida)
            E -= perdida
            lin.avanzar(tr['t_out'], math.sqrt(2.0 * E / m_f))
            ultimo = tr
        if not parado:
            pos = _punto(o, u, ultimo['t_out']) if ultimo else o
            lin.add('exit', ultimo, pos, ultimo['n_out'] if ultimo else u,
                    energy_in_J=E, energy_out_J=E)
        ev += lin.ev
    return ev


def estado_final(objs, salud, eventos):
    """§3.7.3: del dano por objeto al veredicto por Module_Type."""
    modulos = {nm: pr for nm, _, pr in objs if 'Module_Type' in pr}
    fuera = {e['object'] for e in eventos if e.get('out_of_service')}
    por_tipo = {}
    for nm, pr in modulos.items():
        por_tipo.setdefault(pr['Module_Type'], []).append(nm)
    out = {'touched': {e['object']: {'health_J': salud[e['object']],
                                     'out_of_service': e['object'] in fuera}
                       for e in eventos if e['type'] in ('module_hit', 'detonation')}}
    for tipo, nombres in por_tipo.items():
        if tipo in ('Ammo', 'Gun', 'Track'):              # OR entre objetos
            out[tipo] = {'out_of_service': any(n in fuera for n in nombres),
                         'objects': sorted(n for n in nombres if n in fuera)}
        elif tipo == 'Crew':                              # OR dentro de cada tripulante
            miembros = {}
            for nm in nombres:
                miembros.setdefault(nm.split('_')[1], []).append(nm)
            out[tipo] = {k: {'out_of_service': any(n in fuera for n in v),
                             'objects': sorted(n for n in v if n in fuera)}
                         for k, v in sorted(miembros.items())}
        elif tipo in ('Engine', 'Transmission'):          # SUMA de las piezas
            h0 = sum(float(modulos[n]['Health']) for n in nombres)
            h1 = sum(salud[n] for n in nombres)
            out[tipo] = {'health_start_J': round(h0, 1), 'health_end_J': round(h1, 1),
                         'out_of_service': h1 <= 0.0}
        else:                                             # Fuel: cada objeto
            out[tipo] = {n: {'out_of_service': n in fuera} for n in nombres}
    return out


# --- presentacion -----------------------------------------------------------
def resumen(res):
    me = res['meta']
    L = [f"{me['shell']} a {me['distance_m']:.0f} m: {me['impact_velocity_ms']:.0f} m/s, "
         f"{me['impact_energy_J'] / 1e6:.3f} MJ, "
         f"capacidad inicial {me.get('first_layer_capacity_mm', 0):.1f} mm "
         f"(sigma_RHA {me['sigma_RHA_GPa']} GPa, solo informativo)", '']
    for e in res['events']:
        if e['ray_id'] != 0:
            continue
        c = f"cap {e['capacity_in_mm']:.1f}->{e['capacity_out_mm']:.1f}" \
            if 'capacity_out_mm' in e else (f"cap {e['capacity_in_mm']:.1f}"
                                             if 'capacity_in_mm' in e else '')
        en = f"E {e['energy_in_J'] / 1e3:.1f}->{e['energy_out_J'] / 1e3:.1f} kJ" \
            if 'energy_out_J' in e else (f"E {e['energy_in_J'] / 1e3:.1f} kJ"
                                         if 'energy_in_J' in e else '')
        h = f" Health {e['health_in_J']:.0f}->{e['health_out_J']:.0f}" \
            if 'health_in_J' in e else ''
        fuera = ' FUERA' if e.get('out_of_service') else ''
        nf = (f"  {e['n_fragments']} fragmentos de {e['fragment_mass_kg'] * 1000:.1f} g"
              if e['type'] == 'fragment_spawn' else '')
        L.append(f"{e['t_s'] * 1000:8.4f} ms  {e['type']:<14} {e['object']:<28} "
                 f"{e.get('path_mm', 0):7.1f} mm {e.get('angle_deg', 0):5.1f}°  {c}  {en}{h}{fuera}{nf}")
    frag = [e for e in res['events'] if e['ray_id'] != 0]
    if frag:
        paradas = {}
        for e in frag:
            if e['type'] == 'stopped':
                paradas[e['object']] = paradas.get(e['object'], 0) + 1
        top = ', '.join(f"{k} {v}" for k, v in sorted(paradas.items(), key=lambda x: -x[1])[:5])
        L += ['', f"Fragmentos: {len({e['ray_id'] for e in frag})} rayos; "
                  f"{sum(e['type'] == 'exit' for e in frag)} salen del vehiculo; "
                  f"se detienen sobre todo en: {top}"]
        golpes = {}
        for e in frag:
            if e['type'] in ('module_hit', 'detonation'):
                g = golpes.setdefault(e['object'], [0, 0.0, False])
                g[0] += 1
                g[1] += e['energy_in_J'] - e['energy_out_J']
                g[2] = g[2] or e['out_of_service']
        for nm, (k, J, f) in sorted(golpes.items()):
            L.append(f"  {nm:<28} {k:3d} impactos, {J:8.0f} J depositados{' FUERA' if f else ''}")
    L += ['', 'Estado final:']
    for tipo, v in res['final_state'].items():
        if tipo != 'touched':
            L.append(f"  {tipo}: {json.dumps(v, ensure_ascii=False)}")
    for w in me['warnings']:
        L.append(f"AVISO: {w}")
    return '\n'.join(L)


# --- comprobacion -----------------------------------------------------------
def _caja(c, u, v, n, hu, hv, hn):
    def P(a, b, s):
        return tuple(c[i] + a * hu * u[i] + b * hv * v[i] + s * hn * n[i] for i in range(3))
    tris = []
    for fijo in range(3):
        for signo in (-1, 1):
            libres = [i for i in range(3) if i != fijo]
            quad = []
            for pa, pb in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                idx = [0, 0, 0]
                idx[fijo], idx[libres[0]], idx[libres[1]] = signo, pa, pb
                quad.append(P(*idx))
            tris += [(quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])]
    return tris


def _losa(nombre, y, t_mm, theta=0.0, mat='RHA', props=None):
    """Placa de espesor t_mm centrada en y, con la normal inclinada theta del rayo (+Y)."""
    th = math.radians(theta)
    n, v = (0.0, math.cos(th), math.sin(th)), (0.0, -math.sin(th), math.cos(th))
    pr = props or {'Thickness_mm': t_mm, 'Armour_Material': mat}
    return (nombre, _caja((0.0, y, 0.0), (1.0, 0.0, 0.0), v, n, 5.0, 5.0, t_mm / 2000.0), pr)


def _prueba():
    import tempfile
    with tempfile.TemporaryDirectory() as dd:
        def w(nombre, texto):
            open(os.path.join(dd, nombre), 'w').write(texto)
        w('shells.csv', "shell_id,name,type,caliber_mm,core_diameter_mm,mass_kg,"
          "muzzle_velocity_ms,explosive_mass_g,fuze_delay_ms,core_mass_kg,cd\n"
          "T,T,AP,75,,6.8,750,0,,,0.415\n")
        w('penetration.csv', "shell_id,distance_m,angle_deg,penetration_mm,armour_type,"
          "angle_from,thickness_basis,criterion\n"
          "T,100,0,135,RHA,normal,nominal,complete\nT,100,30,106,RHA,normal,nominal,complete\n"
          "T,1000,0,109,RHA,normal,nominal,complete\nT,1000,30,85,RHA,normal,nominal,complete\n")
        w('materials.csv', "id,resistance,spall\nRHA,1.0,1.0\nSteel,0.6,1.0\nFlesh,0.01,0.0\n"
          "Cast_Iron,0.3,1.5\nAmmo,0.2,0.0\n")
        w('velocity.csv', "shell_id,distance_m,velocity_ms\nT,0,750\nT,100,738\nT,1000,636\n")
        w('parametros.csv', "key,value,unit,source\ncontact_gap_mm,1.0,mm,x\n"
          "rho_acero,7850,kg/m3,x\nmasa_fragmento_g,5,g,x\ncono_fragmentos_AP_deg,30,deg,x\n"
          "sigma_fragmento_GPa,3.10,GPa,x\nenergia_minima_fragmento_J,1,J,x\n")
        bd, par = B.BallisticData(dd), cargar_parametros(dd)

    def tiro(objs):
        return disparar(objs, bd, par, 'T', 100.0, (0.0, -1.0, 0.0), (0.0, 1.0, 0.0))

    def tipos(r):
        return [e['type'] for e in r['events']]

    # 1. Ida y vuelta con la tabla: justo por debajo perfora, justo por encima se queda.
    for theta, tabla in ((0.0, 135.0), (30.0, 106.0)):
        assert 'exit' in tipos(tiro([_losa('ARM_P', 0.0, tabla * (1 - 1e-6), theta)]))
        assert tipos(tiro([_losa('ARM_P', 0.0, tabla * 1.001, theta)])) == ['impact', 'stopped']
    r = tiro([_losa('ARM_P', 0.0, 80.0)])
    assert abs(r['meta']['sigma_RHA_GPa'] - 3.105) < 0.005          # §3.7: 3,10 GPa

    # 2. El camino sale de la geometria: 80 mm a 30 grados son 80/cos(30).
    p = tiro([_losa('ARM_P', 0.0, 80.0, 30.0)])['events'][0]
    assert abs(p['path_mm'] - 80 / math.cos(math.radians(30))) < 1e-3

    # 3. Presupuesto cerrado (§1): nucleo + tapon + cizalla = energia de entrada.
    pf = [e for e in r['events'] if e['type'] == 'perforation'][0]
    suma = pf['energy_out_J'] + pf['spall_energy_J'] + pf['shear_energy_J']
    assert abs(suma - pf['energy_in_J']) < 1e-2 and pf['spall_energy_J'] > 0
    assert abs(pf['plug_mass_kg'] - 7850 * 0.080 * math.pi / 4 * 0.075 ** 2) < 1e-3  # §3.5

    # 4. §3.2: dos placas de 70 mm en contacto no son lo mismo que separadas 50 mm.
    pegadas = tiro([_losa('ARM_A', 0.0, 70.0), _losa('ARM_B', 0.070, 70.0)])
    assert tipos(pegadas) == ['impact', 'stopped']                  # 140 > 135
    sueltas = tiro([_losa('ARM_A', 0.0, 70.0), _losa('ARM_B', 0.120, 70.0)])
    assert tipos(sueltas).count('perforation') == 2 and 'exit' in tipos(sueltas)

    # 5. Modulo acumulativo: la salud baja lo que baja la energia. Umbral: no se toca.
    motor = ('MOD_Engine_1', _losa('x', 0.0, 100.0)[1],
             {'Module_Type': 'Engine', 'Health': 3e6, 'Armour_Material': 'Cast_Iron'})
    h = tiro([motor])['events'][0]
    assert abs((h['health_in_J'] - h['health_out_J']) - (h['energy_in_J'] - h['energy_out_J'])) < 1e-2
    assert h['health_out_J'] > 0 and not h['out_of_service']
    crew = ('MOD_Driver_Torso', _losa('x', 0.0, 270.0)[1],
            {'Module_Type': 'Crew', 'Health': 80.0, 'Armour_Material': 'Flesh'})
    rc = tiro([crew])
    h = rc['events'][0]
    assert h['health_in_J'] == h['health_out_J'] == 80.0 and h['out_of_service']
    assert rc['final_state']['Crew']['Driver']['out_of_service']

    # 6. Se queda clavado a la profundidad que le deja la capacidad: 135 / 0,3 = 450 mm.
    gordo = ('MOD_Engine_1', _losa('x', 0.0, 900.0)[1],
             {'Module_Type': 'Engine', 'Health': 3e7, 'Armour_Material': 'Cast_Iron'})
    ev = tiro([gordo])['events']
    st = ev[-1]
    assert [e['type'] for e in ev] == ['module_hit', 'stopped']
    assert abs(st['path_mm'] - 450.0) < 1e-3 and st['energy_out_J'] == 0.0
    assert abs(ev[0]['path_mm'] - 450.0) < 1e-3 and abs(ev[0]['health_in_J'] - ev[0]['health_out_J'] - ev[0]['energy_in_J']) < 1e-2

    # 9. Fragmentos del tapon (§3.6): reparto exacto, semilla fija y dano.
    sp = [e for e in r['events'] if e['type'] == 'fragment_spawn'][0]
    assert abs(sp['energy_in_J'] - pf['spall_energy_J']) < 1e-2
    assert sp['n_fragments'] == round(pf['plug_mass_kg'] / 0.005)
    salen = [e for e in r['events'] if e['ray_id'] != 0 and e['type'] == 'exit']
    assert len(salen) == sp['n_fragments']               # nada detras: todos salen
    assert abs(sum(e['energy_in_J'] for e in salen) - sp['energy_in_J']) < 1.0
    assert json.dumps(r) == json.dumps(tiro([_losa('ARM_P', 0.0, 80.0)]))   # misma semilla
    lado = ('MOD_Driver_Torso', _caja((0.3, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0),
                                      (0.0, 1.0, 0.0), 0.15, 0.15, 0.15),
            {'Module_Type': 'Crew', 'Health': 80.0, 'Armour_Material': 'Flesh'})
    rf = tiro([_losa('ARM_P', 0.0, 80.0), lado])
    toques = [e for e in rf['events'] if e['object'] == 'MOD_Driver_Torso'
              and e['type'] == 'module_hit']
    assert toques and all(e['ray_id'] > 0 and e['parent_id'] == 0 for e in toques)
    assert rf['final_state']['Crew']['Driver']['out_of_service']   # el nucleo no lo toca

    # 7. Ida y vuelta con la tabla real, si esta a mano: cada celda con valor.
    carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    if os.path.exists(os.path.join(carpeta, 'parametros.csv')):
        real, pr = B.BallisticData(carpeta), cargar_parametros(carpeta)
        celdas = 0
        for pid, por_angulo in real.table.items():
            if real.projectiles[pid]['type'] not in CINETICOS:
                continue
            for ang, por_dist in por_angulo.items():
                for dist, mm in por_dist.items():
                    for k, esperado in ((1 - 1e-6, 'exit'), (1.001, 'stopped')):
                        r = disparar([_losa('ARM_P', 0.0, mm * k, ang)], real, pr, pid,
                                     dist, (0.0, -1.0, 0.0), (0.0, 1.0, 0.0))
                        assert esperado in tipos(r), (pid, dist, ang, mm, k)
                    celdas += 1
        print(f"  ida y vuelta con penetration.csv: {celdas} celdas")

        # 8. Regresion de §8 sobre el modelo real: 80 mm nominales a 9 grados son 81,00 mm.
        glb = os.path.join(carpeta, '..', 'models', 'Pz IV H.glb')
        if os.path.exists(glb):
            r = disparar(V.load(glb), real, pr, SHELL, DISTANCIA, ORIGEN, DIRECCION)
            e = r['events'][0]
            assert e['object'] == 'ARM_Upper_Front_Plate', e['object']
            assert abs(e['path_mm'] - 81.0) < 0.01 and abs(e['angle_deg'] - 9.0) < 0.01, e
            print(f"  regresion de §8: {e['object']} {e['path_mm']:.2f} mm {e['angle_deg']:.2f}°")
            # §3.4.2: energia y capacidad salen de la misma cadena, asi que se
            # agotan juntas. Es lo que no cumplia el modelo de dos cuentas.
            assert not [w for w in r['meta']['warnings'] if 'sin energia' in w], \
                r['meta']['warnings']


def _autoprueba():
    _prueba()
    print('selftest OK')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--glb', default=None)
    ap.add_argument('--data', default=None)
    ap.add_argument('--shell', default=SHELL)
    ap.add_argument('--distance', type=float, default=DISTANCIA)
    ap.add_argument('--origin', type=float, nargs=3, default=ORIGEN)
    ap.add_argument('--dir', type=float, nargs=3, default=DIRECCION)
    ap.add_argument('--out', default=None, help='guarda la linea temporal en JSON')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        _autoprueba()
        return 0
    raiz = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    glb = a.glb or os.path.join(raiz, 'models', 'Pz IV H.glb')
    data = a.data or os.path.join(raiz, 'data')
    bd = B.BallisticData(data)
    res = disparar(V.load(glb), bd, cargar_parametros(data), a.shell, a.distance,
                   tuple(a.origin), tuple(a.dir))
    if a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=1, ensure_ascii=False)
    print(resumen(res))
    return 0


if __name__ == '__main__':
    sys.exit(main())

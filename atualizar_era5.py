import cdsapi, time, calendar
from datetime import date, timedelta
from pathlib import Path

c = cdsapi.Client()
AREA = [-5.5, -39.5, -8.75, -34.25]  # [N, W, S, E]
ANO_INI = 2016
JANELA_REVISAO = 90 # dias em que o dado ainda pode ser revisado (ERA5 é reanálise, então pode mudar com o tempo)
LATENCIA = 6 # dias de folga para o ERAT
PASTA = Path("era5_raw"); PASTA.mkdir(exist_ok=True)

HOJE = date.today()
LIMITE = HOJE - timedelta(days=LATENCIA) # último dia seguro de pedir

FALHAS = []

VARIAVEIS = {
    # Temperatura e umidade
    "2m_temperature": "t2m",
    "2m_dewpoint_temperature": "d2m",
    "10m_u_component_of_wind": "u10",
    "10m_v_component_of_wind": "v10",
    "total_precipitation": "tp",                                         
    "volumetric_soil_water_layer_1": "swvl1",            
    "volumetric_soil_water_layer_2": "swvl2",            
    "surface_solar_radiation_downwards": "ssdr",
    "surface_latent_heat_flux": "slhf",
    "surface_sensible_heat_flux": "sshf",                                                    
    "boundary_layer_height": "blh",
    "skin_temperature": "skt",
    "potential_evaporation": "pev",
    "10m_wind_gust_since_previous_post_processing": "fg10",                
    "leaf_area_index_high_vegetation": "lai_hv",          
    "leaf_area_index_low_vegetation": "lai_lv",
    "total_cloud_cover": "tcc",
    "convective_available_potential_energy": "cape",
    "surface_pressure": "sp",
    "total_evaporation": "e",       
}

def baixar(nome_cds, destino, ano, meses, dias, forcar, tentativas=3):
    if destino.exists() and not forcar:
        print(f"[OK] {destino.nome}")
        return
    pedido = {
        "product_type": "reanalysis",
        "variable": [nome_cds],
        "year": [str(ano)],
        "month": [f"{m:02d}" for m in meses],
        "day": [f"{d:02d}" for d in dias],
        "time": [f"{h:02d}:00" for h in range(24)],
        "area": AREA,
        "data_format": "netcdf",
        "donwload_format": "unarchived",
    }

    tmp = destino.with_suffix(".tmp")
    for t in range(1, tentativas+1):
        try:
            print(f"[BAIXANDO] {destino.name} (tentativa {t})")
            c.retrieve("reanalysis-era5-single-levels", pedido, str(tmp))
            tmp.replace(destino)
            return
        except Exception as e:
            print(f"[ERRO] {destino.name}: {e}")
            tmp.unlink(missing_ok=True)
            time.sleep(30 * t)
        print(f"[FALHOU] {destino.name}")
        FALHAS.append(destino.name)

for nome_cds, sigla in VARIAVEIS.items():
    # 1) anos fechados: arquivo anual
    for ano in range(ANO_INI, LIMITE.year):
       fim = date(ano, 12, 31)
       forcar = (HOJE - fim).days <= JANELA_REVISAO # vale em jan-mar
       baixar(nome_cds, PASTA / f"era5_{sigla}_{ano}.nc",
              ano, range(1, 13), range(1, 32), forcar)


    # 2) ano corrente: arquivos mensais
    ano = LIMITE.year
    for mes in range(1, LIMITE.month + 1):
        ultimo = LIMITE.day if mes == LIMITE.month \
                            else calendar.monthrange(ano, mes)[1]
        forcar = (HOJE - date(ano, mes, ultimo)).days <= JANELA_REVISAO
        baixar(nome_cds, PASTA / f"era5_{sigla}_{ano}-{mes:02d}.nc",
               ano, [mes], range(1, ultimo + 1), forcar)

if FALHAS:
    raise SystemExit(f"{len(FALHAS)} falhas: {FALHAS} arquivos falharam: {FALHAS}")

       
import os
from pathlib import Path

# En Vercel solo /tmp es escribible: matplotlib guarda ahí su caché de fuentes
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
import matplotlib
matplotlib.use("Agg")  # backend sin pantalla, necesario en servidores
import matplotlib.pyplot as plt
import pandas as pd
from typing import Optional


from fastapi.responses import HTMLResponse


app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
df = pd.read_csv(BASE_DIR / "ventas_sinteticas.csv")


def sin_nan(d):
    # JSON no admite NaN (p. ej. desviación estándar de un solo dato)
    return {k: (None if pd.isna(v) else v) for k, v in d.items()}


def validar_claves(pedidas, disponibles, nombre):
    faltantes = [p for p in pedidas if p not in disponibles]
    if faltantes:
        raise HTTPException(404, detail=f"{nombre} no encontradas: {', '.join(faltantes)}")
df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>FastAPI Dashboard</title>
            <style>
                body { font-family: sans-serif; background: #121212; color: white; padding: 2rem; text-align: center; }
                a { color: #4af; display: inline-block; margin: 10px; font-size: 1.2rem; }
            </style>
        </head>
        <body>
            <h1>API DE VENTAS </h1>
            <a href="/docs"> Ir a Docs </a> 
        </body>
    </html>
    """

columnas_cuantitativas=["precio_unitario","cantidad","descuento","total"]

        

@app.get("/graficas/precios")
def grafica_precios():
    fig, ax = plt.subplots()
    ax.hist(df["precio_unitario"].dropna(), bins=20)
    ax.set_title("Distribución de precios unitarios")
    ax.set_xlabel("Precio unitario")
    ax.set_ylabel("Frecuencia")

    imagen = BytesIO()
    fig.savefig(imagen, format="png", bbox_inches="tight")
    plt.close(fig)
    imagen.seek(0)

    return StreamingResponse(imagen, media_type="image/png")




## Ejercicios

## 6-A
@app.get("/graficas/histograma/{columna}")
def grafica_columna(columna,num_bins=15):
    if columna not in columnas_cuantitativas:
        raise HTTPException(404, detail="Esa columna no es cuantitativa")

    else:    
        fig, ax = plt.subplots()
        ax.hist(df[columna].dropna(), bins=int(num_bins))
        ax.set_title(f"Distribución de {columna}")
        ax.set_xlabel(f"{columna}")
        ax.set_ylabel("Frecuencia")

        imagen = BytesIO()
        fig.savefig(imagen, format="png", bbox_inches="tight")
        plt.close(fig)
        imagen.seek(0)

        return StreamingResponse(imagen, media_type="image/png")



@app.get("/ventas_x_region")
def ventas(regiones: Optional[str]=None):
    data=df.groupby("region")["total"].sum()

    if regiones:
        regiones_lista=[elem.strip() for elem in regiones.split(",")]
        validar_claves(regiones_lista, data.index, "Regiones")
        return data.loc[regiones_lista].to_dict()
    else:
        return data.to_dict()

#6B
@app.get("/graficas/ventas-tiempo")     ## solo hay que tener cuidado al llamar a fechas no existentes
def serie_de_tiempo(fecha_inicio= "2025-01-02" ,fecha_fin="2025-12-31" ):


    df1 = df.copy()
    df1["fecha"] = pd.to_datetime(df1["fecha"])

    inicio = pd.to_datetime(fecha_inicio)
    fin = pd.to_datetime(fecha_fin)

    df1 = df1[(df1["fecha"] >= inicio) & (df1["fecha"] <= fin)]
    data = df1.groupby("fecha")["cantidad"].sum()

    fig, ax = plt.subplots()
    ax.plot(data.index, data.values)
    ax.set_title("Distribución de ventas diarias")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Cantidad de ventas")

    plt.xticks(rotation=45)
    plt.tight_layout()

    imagen = BytesIO()
    fig.savefig(imagen, format="png", bbox_inches="tight")
    plt.close(fig)
    imagen.seek(0)

    return StreamingResponse(imagen, media_type="image/png")

## 6C
@app.get("/graficas/categorias")
def graficar_categorias (categorias: Optional[str]=None):
    if categorias is None:
        data=df.groupby("categoria")["total"].sum()
    else:
        categorias_lista = [c.strip() for c in categorias.split(",")]
        data = df.groupby("categoria")["total"].sum()
        validar_claves(categorias_lista, data.index, "Categorías")
        data = data.loc[categorias_lista]
    fig, ax = plt.subplots()

    ax.bar(data.index, data.values)
    ax.set_title(f"Ventas por categorías")
    ax.set_xlabel(f"Categoría")
    ax.set_ylabel("Cantidad")

    imagen = BytesIO()
    fig.savefig(imagen, format="png", bbox_inches="tight")
    plt.close(fig)
    imagen.seek(0)

    return StreamingResponse(imagen, media_type="image/png")
    
#7D
@app.post("/calculos/estadisticas")
def metricas(columna: str, categorias: Optional[str] = None):
    if columna not in columnas_cuantitativas:
        raise HTTPException(
            status_code=404, detail="Esa columna no es cuantitativa"
        )

    if categorias:
        categorias_lista = [c.strip() for c in categorias.split(",")]
        df_filtrado = df[df["categoria"].isin(categorias_lista)]
    else:
        df_filtrado = df

    if df_filtrado.empty:
        raise HTTPException(400, detail="No se encontraron datos para las categorías indicadas")

    grouped = df_filtrado.groupby("categoria")[columna]     ## una serie

    # Aquí le pedí a gemini ayuda porque intentaba regresar los pandas dataframe enteros, resultando en error, la solución es convertirlos a diccionario antes
    resultado = {
        "Promedio": sin_nan(grouped.mean().to_dict()),
        "Mediana": sin_nan(grouped.median().to_dict()),
        "Mínimo": sin_nan(grouped.min().to_dict()),
        "Máximo": sin_nan(grouped.max().to_dict()),
        "Desviación estándar": sin_nan(grouped.std().to_dict()),
    }

    return resultado


# 7E
@app.post("/calculos/correlacion")
def corr (columna1, columna2):
    if columna1 not in columnas_cuantitativas or columna2 not in columnas_cuantitativas:
        raise HTTPException (418, detail="Las columnas deben ser cuantitativas")
    else:
        corr_xy = df[columna1].corr(df[columna2], method='pearson')
        return {"mensaje": f"La correlación de Pearson entre las columnas {columna1} y {columna2} es de : {round(corr_xy,4)}"}
    # print(f"\nCorrelación de Pearson entre X y Y: {corr_xy:.4f}")

#7F
@app.post("/calculos/comparacion-regiones")
def comparar (regiones):
    regiones_lista=[region.strip() for region in regiones.split(",")]
    data=df.groupby("region")["total"].sum()
    validar_claves(regiones_lista, data.index, "Regiones")
    data=data.loc[regiones_lista].to_dict()   ## la Series de pandas no se puede convertir a JSON
    return {"Las ventas totales por región son las siguientes" :data}

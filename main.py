from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from io import BytesIO
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

app = FastAPI()
columnas_cuantitativas=["precio_unitario","cantidad","descuento","total"]

RUTA_CSV = Path(__file__).parent / "ventas_sinteticas.csv"
df = pd.read_csv(RUTA_CSV)
df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

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




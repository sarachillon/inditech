import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import requests
from io import BytesIO
import pandas as pd
import argparse
from efficientnet_pytorch import EfficientNet
from torchvision import transforms
from torch import nn

def load_image(url, max_size=(300, 300)):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            img_data = response.content
            image = Image.open(BytesIO(img_data))
            image.thumbnail(max_size, Image.ANTIALIAS)  # Redimensionar manteniendo la relación de aspecto
            return ImageTk.PhotoImage(image)
        else:
            print(f"Error al descargar la imagen desde {url}: Status code {response.status_code}")
            return None
    except Exception as e:
        print(f"Error al procesar la imagen desde {url}: {e}")
        return None

def handle_image_click(search_url, frame, num_columns):
    print("Clicked on image:", search_url)
    df = pd.read_csv("data/inditextech_hackupc_challenge_images.csv")
    prefix = "https://static.zara.net/photos///"
    type = search_url[38:38+6]

    search_response = requests.get(search_url)

    # Verificar si la solicitud fue exitosa
    if search_response.status_code == 200:
        try:
            # Intentar abrir la imagen
            image1 = Image.open(BytesIO(search_response.content)).resize((224, 224))
        except Exception as e:
            print(f"Error al abrir la imagen de búsqueda: {e}")
            exit()

        # Guardar la imagen en disco
        #search_image.save("imagen_current_search.jpg")  # Cambia el formato de imagen si lo deseas

        # Lista para almacenar las similitudes
        similarity_scores = []

        # Bandera para controlar el bucle externo
        terminate_outer_loop = False

        # Iterar sobre cada fila del DataFrame
        for index, row in df.iterrows():
            if terminate_outer_loop:
                break  # Salir del bucle externo si se ha establecido la bandera

            # Obtener las URL de las imágenes de la fila actual
            image_urls = [row[f"IMAGE_VERSION_{3}"]]

            # Filtrar las URL que comiencen con el prefijo
            image_urls_filtered = [url for url in image_urls if isinstance(url, str) and url.startswith(prefix) and type in url]

            # Iterar sobre las URLs de las imágenes filtradas
            for image_url in image_urls_filtered:
                try:
                    # Descargar la imagen desde la URL
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        try:
                            # Intentar abrir la imagen descargada
                            image2 = Image.open(BytesIO(response.content)).resize((224, 224))

                            print(image_url)
                            # Cargar el modelo EfficientNet
                            model = EfficientNet.from_pretrained('efficientnet-b1')
                            model.eval()

                            # Transformar las imágenes a tensores
                            transform = transforms.ToTensor()
                            image1_tensor = transform(image1)
                            image2_tensor = transform(image2)

                            # Añadir una cuarta dimensión representando el número de lote y calcular las características
                            features1 = model.extract_features(image1_tensor.unsqueeze(0))
                            features2 = model.extract_features(image2_tensor.unsqueeze(0))

                            # Aplanar las características y aplicar la similitud del coseno
                            cos = nn.CosineSimilarity(dim=0)
                            similarity = float(cos(features1.flatten(), features2.flatten()))
                            similarity_scores.append((image_url, similarity))

                            #print(f"Cosine similarity between the two images: {similarity:.4f}")

                            # Si ya hemos alcanzado la cantidad deseada de similitudes, establecemos la bandera
                            if len(similarity_scores) >= 50:
                                terminate_outer_loop = True
                                break

                        except Exception as e:
                            print(f"Error al abrir la imagen desde {image_url}: {e}")
                    else:
                        print(f"Error request {image_url}: {response.status_code}")
                except Exception as e:
                    print(f"Error al procesar la imagen desde {image_url}: {e}")

        similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)


        for widget in frame.winfo_children():
            widget.destroy()
        
        print("Top 10 prendas recomendadas:")
        for i, (url, score) in enumerate(similarity_scores[:10]):
            print(f"URL: {url}, Similitud: {score}")

            if pd.notna(url) and url.startswith('http'):
                try:
                    image = load_image(url)
                    if image:
                        label = ttk.Label(frame, image=image)
                        label.image = image  # Guardar una referencia a la imagen
                        label.grid(row=i // num_columns, column=i % num_columns, padx=15, pady=15, sticky='nsew')
                        frame.grid_columnconfigure(i % num_columns, weight=1)
                except Exception as e:
                    print(f"Error al procesar la imagen desde {url}: {e}")


    else:
        print(f"Error al obtener la imagen de búsqueda: {search_response.status_code}")

def main():
    root = tk.Tk()
    root.title("Galería de Imágenes")

    # Calcular número de columnas basado en el ancho de la pantalla
    screen_width = root.winfo_screenwidth()
    image_width = 300 + 20  # Ancho de la imagen más un poco de padding
    num_columns = screen_width // image_width

    # Crear un Canvas y barras de desplazamiento
    canvas = tk.Canvas(root)
    scrollbar_x = ttk.Scrollbar(root, orient='horizontal', command=canvas.xview)
    scrollbar_y = ttk.Scrollbar(root, orient='vertical', command=canvas.yview)
    canvas.configure(xscrollcommand=scrollbar_x.set, yscrollcommand=scrollbar_y.set)

    scrollbar_x.pack(side='bottom', fill='x')
    scrollbar_y.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=True)

    # Crear un frame en el canvas para contener los widgets
    frame = ttk.Frame(canvas)
    canvas.create_window((0, 0), window=frame, anchor='nw')

    df = pd.read_csv("data/inditextech_hackupc_challenge_images.csv")
    image_urls = df.iloc[:20, 2]

    for i, url in enumerate(image_urls):
        if pd.notna(url) and url.startswith('http'):
            try:
                image = load_image(url)
                if image:
                    label = ttk.Label(frame, image=image)
                    label.image = image  # Guardar una referencia a la imagen
                    label.grid(row=i // num_columns, column=i % num_columns, padx=15, pady=15, sticky='nsew')
                    frame.grid_columnconfigure(i % num_columns, weight=1)
                    label.bind("<Button-1>", lambda event, url=url, fr=frame: handle_image_click(url, fr, num_columns))
            except Exception as e:
                print(f"Error al procesar la imagen desde {url}: {e}")

    # Ajuste del tamaño del frame basado en el contenido
    frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox('all'))

    root.mainloop()

if __name__ == "__main__":
    main()
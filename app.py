from flask import Flask, render_template, request
import trimesh
import plotly.graph_objects as go
import tempfile
import os
import pandas as pd
import numpy as np
app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

def try_load_stl(file_path):
    try:
        # trimesh can handle automatic detection and loading of STL files
        mesh = trimesh.load(file_path, file_type='stl')
        return mesh
    except Exception as e:
        print(f"Error loading STL file: {e}")
        return None

def interpolate_temperatures(vertices, thermocouples):
    # Unpack thermocouple data
    therm_x, therm_y, therm_z, therm_temp = thermocouples.T
    therm_points = np.vstack((therm_x, therm_y, therm_z)).T
    
    # Initialize an array to store interpolated temperatures
    interpolated_temps = np.zeros(len(vertices))
    
    # Calculate weights based on inverse distance
    for i, vertex in enumerate(vertices):
        distances = np.linalg.norm(therm_points - vertex, axis=1)
        weights = 1 / np.power(distances, 2)  # Avoid division by zero issues
        weights[distances == 0] = np.inf  # Handle zero distance case
        interpolated_temps[i] = np.sum(weights * therm_temp) / np.sum(weights)
    
    return interpolated_temps

@app.route('/upload', methods=['POST'])
def upload():
    # Expecting two file inputs: one for STL and one for CSV
    stl_file = request.files.get('stl_file')
    csv_file = request.files.get('csv_file')

    if not stl_file or not csv_file:
        return "Both STL and CSV files are required", 400

    # Process STL file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.stl') as tmp_file:
        stl_file.save(tmp_file.name)
        my_mesh = try_load_stl(tmp_file.name)
        if my_mesh is None:
            return "Failed to read STL file", 400
        vertices = my_mesh.vertices /100
        faces = my_mesh.faces
        os.remove(tmp_file.name)  # Clean up the temporary file

    # Read and process CSV data
    df = pd.read_csv(csv_file)
    therm_x = df['x']
    therm_y = df['y']
    therm_z = df['z']
    therm_temp = df['temp']  # Assuming there is a 'temp' column for temperature
    thermocouples = df[['x', 'y', 'z', 'temp']].values

    # Interpolate temperatures
    interpolated_temps = interpolate_temperatures(vertices, thermocouples)  
    # Mesh 3D
    mesh3D = go.Mesh3d(
        x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2],
        i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
        intensity=interpolated_temps,
        opacity=1,
        colorscale='Hot',
        name='Temperature Mesh',
        showscale=True
    )

    #Thermocouples as scatter points
    scatter = go.Scatter3d(
        x=therm_x,
        y=therm_y,
        z=therm_z,
        mode='markers+text',
        marker=dict(size=5, color=therm_temp, colorscale='Hot', showscale=True),
        text=therm_temp,
        name='Thermocouples'
    )

    # Plotly layout
    layout = go.Layout(
        title="3D Model with Thermocouple Positions",
        width=800,
        height=800,
        scene=dict(
            xaxis=dict(title='X'),
            yaxis=dict(title='Y'),
            zaxis=dict(title='Z'),
            aspectmode='data'
        )
    )



    # Combine both plots
    fig = go.Figure(data=[mesh3D, scatter], layout=layout)
    #fig = go.Figure(data=[mesh3D], layout=layout)
    plot_div = fig.to_html(full_html=False, include_plotlyjs=True)

    return render_template('view.html', plot=plot_div)

if __name__ == '__main__':
    app.run(debug=True)

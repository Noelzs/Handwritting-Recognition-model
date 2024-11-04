import os
import cv2
import typing
import numpy as np
import requests
from flask import Flask, request, render_template
from flask_pymongo import PyMongo
from pymongo import MongoClient
from mltu.inferenceModel import OnnxInferenceModel
from mltu.utils.text_utils import ctc_decoder
from mltu.configs import BaseModelConfigs

class ImageToWordModel(OnnxInferenceModel):
    def __init__(self, char_list: typing.Union[str, list], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.char_list = char_list

    def predict(self, image: np.ndarray):
        image = cv2.resize(image, self.input_shapes[0][1:3][::-1])
        image_pred = np.expand_dims(image, axis=0).astype(np.float32)
        preds = self.model.run(self.output_names, {self.input_names[0]: image_pred})[0]
        text = ctc_decoder(preds, self.char_list)[0]
        return text

app = Flask(__name__)

# MongoDB configuration
app.config["MONGO_URI"] = "mongodb://localhost:27017/DataLogs"
mongo = PyMongo(app)
client = MongoClient('mongodb://localhost:27017/DataLogs')
db = client['DataLogs']

try:
    client.admin.command('ping')
    print("Connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")


# Load the model configuration
configs = BaseModelConfigs.load("Models/HandrwrittingRecognition/202410272400/configs.yaml")
model = ImageToWordModel(model_path=configs.model_path, char_list=configs.vocab)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        patient_name = request.form['patient_name']
        doctor_name = request.form['doctor_name']
        hospital_name = request.form['hospital_name']
        prescription_file = request.files['prescription_file']

        print("Received form data:")
        print(f"Patient Name: {patient_name}")
        print(f"Doctor Name: {doctor_name}")
        print(f"Hospital Name: {hospital_name}")


        # Save the uploaded file
        file_path = os.path.join('static/uploads', prescription_file.filename)
        prescription_file.save(file_path)
        print(f"File saved to: {file_path}")

        # Read the image and predict
        image = cv2.imread(file_path)
        if image is None:
            print("Error: Image not read correctly.")
            return render_template('index2.html', result="Error reading image.")

        print("Image read successfully. Proceeding with prediction...")
        interpreted_word = model.predict(image)
        print(f"Interpreted Word: {interpreted_word}")

        # Initialize variables with default values
        purpose = 'N/A'
        warnings = 'N/A'
        dosage = 'N/A'
        keep_out_of_reach = 'N/A'
        pregnancy = 'N/A'
        stop_use = 'N/A'

        # Call OpenFDA API
        medicine_details = call_openfda_api(interpreted_word)
        print(f"Medicine Details: {medicine_details}")
        # Check if the API returned any data
        
        if medicine_details and 'results' in medicine_details:
            # Safely access results
            results = medicine_details['results'][0] if medicine_details['results'] else {}
            purpose = results.get('purpose', 'N/A')
            keep_out_of_reach = results.get('keep_out_of_reach_of_children', 'N/A')
            warnings = results.get('warnings', 'N/A')
            dosage = results.get('dosage_and_administration', 'N/A')
            pregnancy = results.get('pregnancy_or_breast_feeding', 'N/A')
            stop_use = results.get('stop_use', 'N/A')

            # Save the data to MongoDB
            try:
                mongo.db.prescriptions.insert_one({
                    'patient_name': patient_name,
                    'doctor_name': doctor_name,
                    'hospital_name': hospital_name,
                    'interpreted_word': interpreted_word,
                    'purpose': purpose,
                    'keep_out_of_reach_of_children': keep_out_of_reach,
                    'warnings': warnings,
                    'dosage_and_administration': dosage,
                    'pregnancy_or_breast_feeding': pregnancy,
                    'stop_use': stop_use
                })

            except Exception as e:
                print(f"Error saving to MongoDB: {e}")

        return render_template('result.html', patient_name=patient_name,
                               doctor_name=doctor_name,
                               hospital_name=hospital_name,
                               interpreted_word=interpreted_word,
                               purpose=purpose,
                               warnings=warnings,
                               dosage=dosage,
                               keep_out_of_reach=keep_out_of_reach,
                               pregnancy=pregnancy,
                               stop_use=stop_use)

    return render_template('index.html')

def call_openfda_api(interpreted_word):
    url = f"https://api.fda.gov/drug/label.json?search={interpreted_word}&limit=1"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return {}

if __name__ == '__main__':
    app.run(debug=True)

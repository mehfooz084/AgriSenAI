import os

# Must be set before TensorFlow is imported
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import numpy as np
import tensorflow as tf
import tf_keras as keras
from tf_keras.utils import load_img, img_to_array


# ============================================================
# MODEL PATH
# ============================================================

MODEL_PATH = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    ),
    "model",
    "best_mobilenetv2.h5"
)


# ============================================================
# CLASS NAMES
# ============================================================

CLASS_NAMES = [
    "Apple - Apple Scab",
    "Apple - Black Rot",
    "Apple - Cedar Apple Rust",
    "Apple - Healthy",
    "Bell Pepper - Bacterial Spot",
    "Bell Pepper - Healthy",
    "Cherry - Healthy",
    "Cherry - Powdery Mildew",
    "Corn (Maize) - Cercospora Leaf Spot",
    "Corn (Maize) - Common Rust",
    "Corn (Maize) - Healthy",
    "Corn (Maize) - Northern Leaf Blight",
    "Grape - Black Rot",
    "Grape - Esca (Black Measles)",
    "Grape - Healthy",
    "Grape - Leaf Blight",
    "Peach - Bacterial Spot",
    "Peach - Healthy",
    "Potato - Early Blight",
    "Potato - Healthy",
    "Potato - Late Blight",
    "Strawberry - Healthy",
    "Strawberry - Leaf Scorch",
    "Tomato - Bacterial Spot",
    "Tomato - Early Blight",
    "Tomato - Healthy",
    "Tomato - Late Blight",
    "Tomato - Septoria Leaf Spot",
    "Tomato - Yellow Leaf Curl Virus"
]


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}"
        )

    print("=" * 60)
    print("LOADING MODEL...")
    print("=" * 60)

    print("Model:", MODEL_PATH)
    print(
        "TF_USE_LEGACY_KERAS:",
        os.environ.get("TF_USE_LEGACY_KERAS")
    )

    try:

        # ----------------------------------------------------
        # Explicitly import the legacy TFOpLambda layer
        # ----------------------------------------------------

        try:
            from tf_keras.src.layers.core.tf_op_layer import TFOpLambda
        except Exception:
            from tensorflow.python.keras.layers.core import TFOpLambda

        print(
            "TFOpLambda loaded:",
            TFOpLambda,
            flush=True
        )

        # ----------------------------------------------------
        # Explicit custom object mapping
        # ----------------------------------------------------

        custom_objects = {
            "TFOpLambda": TFOpLambda
        }

        print(
            "Custom objects:",
            list(custom_objects.keys()),
            flush=True
        )

        # ----------------------------------------------------
        # Load old H5 model
        # ----------------------------------------------------

        model = keras.models.load_model(
            MODEL_PATH,
            custom_objects=custom_objects,
            compile=False
        )

        print("=" * 60)
        print("MODEL LOADED SUCCESSFULLY")
        print("=" * 60)

        print(
            "Input Shape:",
            model.input_shape
        )

        print(
            "Output Shape:",
            model.output_shape
        )

        return model

    except Exception as e:

        print("=" * 60)
        print("MODEL LOAD ERROR")
        print("=" * 60)

        print(
            "ERROR TYPE:",
            type(e).__name__,
            flush=True
        )

        print(
            "ERROR:",
            str(e),
            flush=True
        )

        print("=" * 60)

        raise


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def preprocess_image(image_file):

    image_file.seek(0)

    img = load_img(
        image_file,
        target_size=(224, 224)
    )

    print("=" * 60)
    print("IMAGE PREPROCESSING")
    print("=" * 60)

    print(
        "Original Image Size:",
        img.size
    )

    img_array = img_to_array(img)

    print(
        "Image Shape:",
        img_array.shape
    )

    print(
        "Image dtype:",
        img_array.dtype
    )

    print(
        "Pixel Min:",
        img_array.min()
    )

    print(
        "Pixel Max:",
        img_array.max()
    )

    print(
        "Pixel Mean:",
        img_array.mean()
    )

    img_array = np.expand_dims(
        img_array,
        axis=0
    )

    print(
        "Final Shape:",
        img_array.shape
    )

    print("=" * 60)

    return img_array


# ============================================================
# PREDICT DISEASE
# ============================================================

def predict_disease(image_file, model):

    try:

        img = preprocess_image(
            image_file
        )

        predictions = model.predict(
            img,
            verbose=0
        )[0]

        class_idx = int(
            np.argmax(predictions)
        )

        confidence = (
            float(predictions[class_idx])
            * 100
        )

        predicted_class = CLASS_NAMES[
            class_idx
        ]

        print("=" * 60)
        print("PREDICTION RESULTS")
        print("=" * 60)

        print(
            "Predicted Index:",
            class_idx
        )

        print(
            "Predicted Class:",
            predicted_class
        )

        print(
            "Confidence: {:.2f}%".format(
                confidence
            )
        )

        print("\nTop 5 Predictions")
        print("-" * 60)

        top5 = np.argsort(
            predictions
        )[-5:][::-1]

        for idx in top5:

            print(
                f"{CLASS_NAMES[idx]:45s} "
                f"{predictions[idx] * 100:.2f}%"
            )

        print("=" * 60)

        return (
            predicted_class,
            confidence
        )

    except Exception as e:

        print("=" * 60)
        print("PREDICTION ERROR")
        print("=" * 60)

        print(
            "ERROR TYPE:",
            type(e).__name__,
            flush=True
        )

        print(
            "ERROR:",
            str(e),
            flush=True
        )

        print("=" * 60)

        raise

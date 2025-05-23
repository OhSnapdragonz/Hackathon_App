from detector import Detector
from retriever import Retriever
from fifocache import FIFOCache
import re
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np
from pokemontcgsdk import Card
from pokemontcgsdk import RestClient
import asyncio
import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
RestClient.configure('c0a13e31-4371-413c-8f1f-264697acc48e')  # my API key


def get_bbox_corner(bbox, img):
    x, y, w, h = bbox
    x_min = int(x - w / 2)
    y_min = int(y - h / 2)
    x_max = int(x + w / 2)
    y_max = int(y + h / 2)

    height, width, _ = img.shape
    x_min = max(0, x_min)
    y_min = max(0, y_min)
    x_max = min(width, x_max)
    y_max = min(height, y_max)

    return x_min, y_min, x_max, y_max

def get_segmented_card(mask, bbox, img):
    resized_mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    
    # get masked pixels
    cutout = resized_mask[..., None]*img

    # Get bounding box coordinates (x, y, width, height, conf, label)
    x_min, y_min, x_max, y_max = get_bbox_corner(bbox, img)

    # Crop to bounding box
    cropped_cutout = cutout[y_min:y_max, x_min:x_max]

    # Convert to PIL image
    cropped_cutout = Image.fromarray((cropped_cutout * 255).astype(np.uint8))

    return cropped_cutout

def process_card(mask, bbox, img, track_id, ret, results, cache):
    x_min, y_min, x_max, y_max = get_bbox_corner(bbox, img)

    # Convert to PIL image
    cropped_cutout = get_segmented_card(mask, bbox, img)

    # Get card id
    matches = ret.get_card_id(cropped_cutout)
    card_id = matches[0]
    if card_id in cache:
        card = cache.get(card_id)  # if in cache
    else:
        card = Card.find(card_id)  # if not in cache
        cache.put(card_id, card)

    # Store the result
    results.append(f"Track id {track_id}: {card.name}")

    # Draw bounding box and label on the original image
    cv2.rectangle(img, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)
    label = f"ID: {track_id} - {card.name}"
    cv2.putText(img, label, (x_min, y_min + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

def process_all_cards(masks, bboxs, img, track_ids, ret, cache):
    tasks = []
    results = []

    # Loop over masks and create asynchronous tasks for each card
    for i in range(len(masks)):
        task = process_card(masks[i], bboxs[i], img, track_ids[i], ret, results, cache)
        tasks.append(task)

    # Wait for all tasks to complete

    # After the loop completes, print the results
    for result in results:
        print(result)

# Main function to run the model, track and process the image
def main():
    
    det = Detector("res\\detection_weights\\yolo11n_seg_best_10epochs.onnx")
    ret = Retriever("res\\classfication_embeddings\\ResNet18_embeddings.pt")
    cards_cache = FIFOCache(30)

    img = cv2.imread("res\\test.jpg")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = det.model.track("res\\test.jpg")
    result = results[0]
    result.show()

    masks = (result.masks.data.numpy() * 255).astype("uint8")
    bboxs = result.boxes.xywh.data.numpy()
    track_ids = results[0].boxes.id.int().cpu().tolist()

    process_all_cards(masks, bboxs, img, track_ids, ret, cards_cache)

    # Display the final image with bounding boxes and labels
    plt.imshow(img)
    plt.show()

# Run the asynchronous main functio
main()

import math
import os
from PIL import Image, ImageDraw
import numpy as np
from ipycanvas import Canvas
from .card import Card


CANVAS_SIZE = (800, 500)
canvas = Canvas(width=CANVAS_SIZE[0], height=CANVAS_SIZE[1])
script_directory = os.path.dirname(os.path.abspath(__file__))
CARDS_IMAGE_PATH = os.path.join(script_directory, "../images/cards.png")
POINT_IMAGE_PATH = os.path.join(script_directory, "../images/point.png")
POINT_IMAGE = np.array(Image.open(POINT_IMAGE_PATH).resize((30, 30)))


def calculate_coordinates(center_pos: tuple, start_pos: tuple, angle_at_a: float):
    # Compute the position of a player given the position of the first player
    # the center position and the angle at which he is on the table relative
    # to the first player

    x1 = center_pos[0]
    y1 = center_pos[1]

    x2 = start_pos[0]
    y2 = start_pos[1]
    # Calculate the length of AB
    ab_length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    # Normalize AB vector
    abx_normalized = (x2 - x1) / ab_length
    aby_normalized = (y2 - y1) / ab_length

    # Convert the angle from degrees to radians
    theta = math.radians(angle_at_a)

    # Rotate the normalized AB vector
    x3 = abx_normalized * math.cos(theta) - aby_normalized * math.sin(theta)
    y3 = abx_normalized * math.sin(theta) + aby_normalized * math.cos(theta)

    # Scale the rotated vector to the length of AB
    x3 *= ab_length
    y3 *= ab_length

    # Calculate the coordinates of vertex C
    x3 += x1
    y3 += y1

    return x3, y3


def keep_image_center(image_matrix):
    # Truncate card images and set transparent mask

    # Add an alpha channel with value 255 for all pixels
    alpha_channel = np.full(
        (image_matrix.shape[0], image_matrix.shape[1], 1), 255, dtype=np.uint8
    )
    image_matrix = np.concatenate((image_matrix, alpha_channel), axis=2)

    # Create a blank transparent image with the same shape as the original image
    transparent_image = Image.new(
        "RGBA", (image_matrix.shape[1], image_matrix.shape[0]), (0, 0, 0, 0)
    )

    # Create an ImageDraw object to draw on the transparent image
    draw = ImageDraw.Draw(transparent_image)

    # Get the center coordinates of the image
    center_x = image_matrix.shape[1] // 2
    center_y = image_matrix.shape[0] // 2

    # Define the radius of the circle
    radius = 130

    # Draw a solid white circle on the transparent image
    draw.ellipse(
        (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
        fill=(255, 255, 255, 255),
    )

    # Convert the transparent image to a NumPy array
    transparent_array = np.array(transparent_image)

    # Create a mask for the circle by checking if the alpha channel is not zero
    circle_mask = transparent_array[:, :, 3] != 0

    # Create a copy of the original image matrix
    modified_image_matrix = np.copy(image_matrix)

    # Make the pixels outside the circle transparent (set alpha channel to zero)
    modified_image_matrix[~circle_mask] = [0, 0, 0, 0]
    modified_image = Image.fromarray(modified_image_matrix)
    modified_image = modified_image.resize((50, 50))
    return np.array(modified_image)


def load_cards():
    image = Image.open(CARDS_IMAGE_PATH)
    array = np.array(image)
    width, _ = image.size
    parts_width = int(width / 3)
    skull = keep_image_center(array[:, 0:parts_width])
    flower = keep_image_center(array[:, parts_width: parts_width * 2])
    hidden = keep_image_center(array[:, parts_width * 2:])
    return skull, flower, hidden


SKULL_IMAGE, FLOWER_IMAGE, HIDDEN_CARD_IMAGE = load_cards()
card_skins = {
    Card.FLOWER: FLOWER_IMAGE,
    Card.SKULL: SKULL_IMAGE,
    Card.hidden: HIDDEN_CARD_IMAGE
}


def get_canvas(state: 'BoardState') -> Canvas:  # type: ignore
    canvas.clear()
    canvas.stroke_style = "black"
    canvas.stroke_rect(0, 0, CANVAS_SIZE[0], CANVAS_SIZE[1])
    canvas.fill_style = "green"
    canvas.fill_circle(CANVAS_SIZE[0] / 2, CANVAS_SIZE[1] / 2,  min(CANVAS_SIZE) / 2)
    offset = 360 / len(state.players)
    angle: float = 0
    center_pos = (CANVAS_SIZE[0] / 2, CANVAS_SIZE[1] / 2)
    start_pos = (CANVAS_SIZE[0] / 2, CANVAS_SIZE[1] - 50)
    for player in state.players:
        angle += offset
        stack_posx, stack_posy = calculate_coordinates(center_pos, start_pos, angle)
        hand_posx, hand_posy = calculate_coordinates(center_pos, start_pos, angle - 20)
        if player.points:
            points_posx, points_posy = calculate_coordinates(
                center_pos, start_pos, angle + 20
            )
            canvas.put_image_data(
                POINT_IMAGE,
                points_posx,
                points_posy,
            )
        canvas.stroke_style = "red"
        canvas.stroke_circle(stack_posx, stack_posy, 30)
        canvas.stroke_style = "white"
        canvas.stroke_circle(hand_posx, hand_posy, 30)
        of = -25
        for card in player.cards_hand:
            canvas.put_image_data(card_skins[card], hand_posx + of, hand_posy + of)
            of += 5
        of = -25
        for card in player.cards_stack:
            canvas.put_image_data(card_skins[card], stack_posx + of, stack_posy + of)
            of += 5
        for card in player.cards_revealed:
            canvas.put_image_data(card_skins[card], stack_posx + of, stack_posy + of)
            of += 5
    return canvas

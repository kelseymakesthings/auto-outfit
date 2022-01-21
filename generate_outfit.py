import argparse
import json
import os
import random

import numpy as np
from PIL import Image

CLOSET_FILENAME = "closet.json"
IMAGES_PATH = "images"


class Outfit:
    def __init__(self, policy, closet):
        self.policy = policy
        self.order = ["top", "bottom", "jacket", "shoe"]
        self.piece_type_to_list = {
            "top": closet["tops"],
            "bottom": closet["bottoms"],
            "jacket": closet["jackets"],
            "shoe": closet["shoes"],
        }

    def generate(self):
        self.__randomize_piece_lists()  # To generate a random outfit each time
        outfit = self.__get_valid_outfit()

        # Print the names of all pieces and display pictures
        print(
            "Your outfit for today:",
            ", ".join([outfit[piece]["name"] for piece in self.order]),
        )
        self.__display_outfit([outfit[piece]["filename"] for piece in self.order])

    def __randomize_piece_lists(self):
        for piece_type, list in self.piece_type_to_list.items():
            self.piece_type_to_list[piece_type] = random.sample(list, len(list))

    def __get_valid_outfit(self):
        first_piece_type = self.order[0]
        to_explore = [
            (first_piece_type, p) for p in self.piece_type_to_list[first_piece_type]
        ]
        outfit = {}
        while len(to_explore) > 0:
            piece_type, piece = to_explore.pop()
            outfit[piece_type] = piece
            if self.policy.is_valid(**outfit):
                if len(outfit) == len(self.order):
                    return outfit
                next_piece_type = self.__get_next_piece_type(piece_type)
                to_explore.extend(
                    [
                        (next_piece_type, p)
                        for p in self.piece_type_to_list[next_piece_type]
                    ]
                )
            else:
                del outfit[piece_type]
        raise Exception(
            "Outfit cannot be generated with existing closet and constraints"
        )

    def __display_outfit(self, filenames):
        images = [
            Image.open(os.path.join(IMAGES_PATH, filename)) for filename in filenames
        ]
        image_stack = np.hstack(images)
        Image.fromarray(np.rot90(image_stack, 3)).show()

    def __get_next_piece_type(self, curr_piece_type):
        return self.order[self.order.index(curr_piece_type) + 1]


class OutfitPolicy:
    def __init__(self, warmth_level, comfort_level, fancy, required_piece, closet):
        self.warmth_level, self.fancy, self.comfort_level, self.required_piece = (
            warmth_level,
            fancy,
            comfort_level,
            required_piece,
        )
        self.piece_type_to_list = {
            "top": closet["tops"],
            "bottom": closet["bottoms"],
            "jacket": closet["jackets"],
            "shoe": closet["shoes"],
        }
        if self.required_piece:
            self.required_piece_type = self.__get_piece_type_from_name(
                self.required_piece
            )
        self.neutral_colors = ["black", "white", "tan", "gray", "jeanblue"]
        self.piece_type_to_piece = {}

    def is_valid(self, top=None, bottom=None, jacket=None, shoe=None):
        # Determines if outfit (partial or full) satisfies policy
        self.piece_type_to_piece = {
            "top": top,
            "bottom": bottom,
            "jacket": jacket,
            "shoe": shoe,
        }
        return (
            self.__is_color_matched()
            and self.__has_silhouette(top, bottom)
            and (not self.warmth_level or self.__meets_warmth_level(bottom, jacket))
            and (not self.comfort_level or self.__meets_comfort_level())
            and (not self.fancy or self.__is_fancy())
            and (
                not self.required_piece
                or self.__contains_required_piece_for_piece_type()
            )
        )

    def __meets_warmth_level(self, bottom, jacket):
        return (
            bottom is None or bottom["attributes"]["warmth"] == self.warmth_level
        ) and (jacket is None or jacket["attributes"]["warmth"] == self.warmth_level)

    def __meets_comfort_level(self):
        for piece in self.piece_type_to_piece.values():
            if piece and piece["attributes"]["comfort"] < self.comfort_level:
                return False
        return True

    def __is_fancy(self):
        for piece in self.piece_type_to_piece.values():
            if piece and not piece["attributes"]["fancy"]:
                return False
        return True

    def __contains_required_piece_for_piece_type(self):
        for piece_type, piece in self.piece_type_to_piece.items():
            if (
                piece
                and self.required_piece_type == piece_type
                and piece["name"] != self.required_piece
            ):
                return False
        return True

    def __is_color_matched(self):
        # An outfit can have maximum 1 non-neutral color
        colors = []
        for piece in self.piece_type_to_piece.values():
            if piece and piece["attributes"]["color"] not in self.neutral_colors:
                colors.append(piece["attributes"]["color"])
        return len(set(colors)) <= 1

    def __has_silhouette(self, top, bottom):
        # Either top or bottom (or neither) can be loose, but not both
        return not (
            top
            and bottom
            and top["attributes"]["loose"]
            and bottom["attributes"]["loose"]
        )

    def __get_piece_type_from_name(self, piece_name):
        for piece_type, pieces in self.piece_type_to_list.items():
            if len(list(filter(lambda p: p["name"] == piece_name, pieces))) > 0:
                return piece_type
        raise argparse.ArgumentTypeError(
            "Required piece name not found. Make sure the name exists in your closet"
        )


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Generate a random outfit according to kelsey makes things's style rules")
    parser.add_argument(
        "-w",
        "--warmth",
        type=int,
        choices=range(1, 4),
        help="specific warmth level for bottom and jacket",
    )
    parser.add_argument(
        "-c",
        "--comfort",
        type=int,
        choices=range(1, 4),
        help="minimum comfort level for all pieces",
    )
    parser.add_argument(
        "-f",
        "--fancy",
        action="store_true",
        help="if specified, all pieces must be fancy",
    )
    parser.add_argument(
        "-i", "--include", type=str, help="required piece name to include"
    )
    args = parser.parse_args()

    closet = None
    # Read from closet file
    with open(CLOSET_FILENAME, "r") as f:
        closet = json.load(f)

    # Create outfit policy and generate outfit
    policy = OutfitPolicy(args.warmth, args.comfort, args.fancy, args.include, closet)
    Outfit(policy, closet).generate()

"""
Rin Chat nodes for ComfyUI.

Two nodes. One supplies the values Rin Chat controls, one collects the picture. Everything else about the
workflow stays yours: samplers, LoRAs, upscalers, ControlNet.

THE RULE THAT SHAPES ALL OF THIS: the workflow must still work in ComfyUI on its own.

So the input node is just a box of values with defaults. Press Queue in ComfyUI and it emits exactly what
you typed into it, like any primitive. When Rin Chat runs the workflow it replaces those values before
queueing; when nobody is driving, nothing is missing and nothing errors. A workflow you build for Rin Chat
stays a workflow you can develop, debug and share normally.

HOW RIN CHAT FINDS IT
---------------------
By `class_type` — not by node id (which changes when you edit a graph) and not by node title (a convention
people mistype). The `key` widget only matters if you have MORE THAN ONE input node in a workflow; with a
single one, leave it blank and it just works.

Rin Chat sets: positive, negative, width, height, seed, and — if the provider has them set — steps and cfg.
Wire up only the outputs you need; the rest can dangle.
"""

import json
import os
import random

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

import folder_paths

CATEGORY = "Rin Chat"

KEY_HINT = (
    "Optional. Leave blank unless this workflow has more than one Rin Chat Input — then set a name here "
    "and the same one on the provider in Rin Chat."
)


class RinChatInput:
    """Every value Rin Chat drives, in one node.

    THREE WAYS A VALUE ARRIVES, in order of precedence:

      1. Rin Chat sends it — it replaces whatever was there.
      2. Something is connected to that field — drag a link onto any widget and ComfyUI converts it to an
         input, so you can feed it from your own nodes. That value is used whenever Rin Chat sends nothing.
      3. Nothing else — the value typed here.

    Which means the same graph serves both masters: wire your own defaults in, press Queue, and it renders
    them; let Rin Chat drive, and it overrides only the fields it actually has. Steps and CFG, for
    instance, are only sent if they're set on the provider — otherwise your numbers stand.

    Unused outputs are fine. Wire only what your graph needs.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive": ("STRING", {"default": "", "multiline": True,
                                        "tooltip": "The full positive prompt, with any style and character prefixes already applied."}),
                "negative": ("STRING", {"default": "", "multiline": True,
                                        "tooltip": "The negative prompt."}),
                "width": ("INT", {"default": 1024, "min": 16, "max": 16384, "step": 8}),
                "height": ("INT", {"default": 1024, "min": 16, "max": 16384, "step": 8}),
                # control_after_generate is what makes repeated queueing in ComfyUI produce different
                # pictures — the behaviour anyone expects of a seed. Rin Chat sets the number when it drives,
                # so both sides behave the way their own user expects.
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF, "control_after_generate": True}),
                "steps": ("INT", {"default": 25, "min": 1, "max": 10000,
                                  "tooltip": "Rin Chat only replaces this if Steps is set on the provider."}),
                "cfg": ("FLOAT", {"default": 6.0, "min": 0.0, "max": 100.0, "step": 0.1,
                                  "tooltip": "Rin Chat only replaces this if CFG is set on the provider."}),
                "key": ("STRING", {"default": "", "multiline": False, "tooltip": KEY_HINT}),
            },
            # OPTIONAL, deliberately: workflows saved before these fields existed still validate when
            # submitted over the API — a missing optional widget just takes the function default.
            "optional": {
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 64,
                                       "tooltip": "How many images per run. Rin Chat sets this (its batch, or 1); wire it to your latent's batch_size."}),
                "from_api": ("BOOLEAN", {"default": False,
                                         "tooltip": "Leave OFF. Rin Chat switches this on when it drives the workflow — wire the outputs to a switch to bypass nodes that should only run for local queues (or only for Rin Chat)."}),
                "project": ("STRING", {"default": "",
                                       "tooltip": "Free text for your workflow's own use — filename prefixes, folder routing. Rin Chat's Image Studio replaces it when its Project field is filled in; otherwise what you type here stands."}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT", "INT", "INT", "FLOAT", "INT", "BOOLEAN", "INT", "STRING")
    RETURN_NAMES = ("positive", "negative", "width", "height", "seed", "steps", "cfg", "batch_size", "from_api", "from_api_int", "project")
    FUNCTION = "get"
    CATEGORY = CATEGORY
    DESCRIPTION = "The values Rin Chat controls. Falls back to what's connected, then to what you type here."

    def get(self, positive, negative, width, height, seed, steps, cfg, key, batch_size=1, from_api=False,
            project=""):
        # from_api twice: as a BOOLEAN for boolean switches, and as 1/0 for the index-style ones.
        return (positive, negative, int(width), int(height), int(seed), int(steps), float(cfg),
                int(batch_size), bool(from_api), 1 if from_api else 0, str(project))


class RinChatOutput:
    """Where Rin Chat collects the finished picture.

    Behaves like Preview Image when you use ComfyUI on its own: the picture appears in the node, and the
    file goes to the TEMP directory rather than your output folder — driving a chat shouldn't quietly fill
    your disk with every reroll. Add your own Save Image alongside if you want copies kept.
    """

    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        # Same scheme ComfyUI's own PreviewImage uses, so two queued runs can't overwrite each other's files.
        self.prefix_append = "_rinchat_" + "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(5))
        self.compress_level = 1

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "key": ("STRING", {"default": "", "multiline": False, "tooltip": KEY_HINT}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "collect"
    OUTPUT_NODE = True
    CATEGORY = CATEGORY
    DESCRIPTION = "Rin Chat picks the picture up here. Previews in ComfyUI; writes to temp, not output."

    def collect(self, images, key, prompt=None, extra_pnginfo=None):
        prefix = (key or "rinchat") + self.prefix_append
        full_path, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
            prefix, self.output_dir, images[0].shape[1], images[0].shape[0]
        )
        results = []
        for image in images:
            array = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8))

            # The workflow travels in the PNG, same as every other ComfyUI output — so a picture Rin Chat
            # produced can be dragged back into ComfyUI and edited. Losing that would make these images
            # second-class next to the ones the same graph produces standalone.
            metadata = PngInfo()
            if prompt is not None:
                metadata.add_text("prompt", json.dumps(prompt))
            if extra_pnginfo is not None:
                for k in extra_pnginfo:
                    metadata.add_text(k, json.dumps(extra_pnginfo[k]))

            name = f"{filename}_{counter:05}_.png"
            img.save(os.path.join(full_path, name), pnginfo=metadata, compress_level=self.compress_level)
            results.append({"filename": name, "subfolder": subfolder, "type": self.type})
            counter += 1

        # `images` is what ComfyUI shows in the node AND what appears under this node in /history, which is
        # exactly how Rin Chat finds the result. One structure serves both readers.
        return {"ui": {"images": results}}


NODE_CLASS_MAPPINGS = {
    "RinChatInput": RinChatInput,
    "RinChatOutput": RinChatOutput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RinChatInput": "Rin Chat · Input",
    "RinChatOutput": "Rin Chat · Output",
}

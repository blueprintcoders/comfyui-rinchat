# ComfyUI — Rin Chat nodes

Two ComfyUI nodes that let [Rin Chat](https://github.com/blueprintcoders) drive **your own ComfyUI workflow** as its image backend: one node supplies the values Rin Chat controls, one collects the finished picture. Everything else about the workflow stays yours — samplers, LoRAs, upscalers, ControlNet, whatever you've built.

The rule that shapes all of this: **the workflow must still work in ComfyUI on its own.** The input node is just a box of values with defaults — press Queue in ComfyUI and it emits exactly what you typed into it, like any primitive. When Rin Chat runs the workflow it replaces those values before queueing; when nobody is driving, nothing is missing and nothing errors.

## Install

Copy (or clone) this folder into ComfyUI's `custom_nodes` directory and restart ComfyUI:

```
ComfyUI/custom_nodes/comfyui-rinchat/
```

The nodes appear under the **Rin Chat** category: **Rin Chat · Input** and **Rin Chat · Output**.

## Set-up

1. Add **Rin Chat · Input** to your workflow and wire the outputs you need — prompt into your text encoders, width/height into your latent, seed into your sampler. Unused outputs can dangle.
2. Feed your final image into **Rin Chat · Output**.
3. Press **Queue once** in ComfyUI. That's the whole setup: Rin Chat adopts the last workflow you queued that contains these nodes, and re-adopts automatically whenever you edit and Queue again. No file exports, no re-configuring.
4. In Rin Chat: *Settings → Image providers → ComfyUI*, point it at your server (e.g. `http://localhost:8188`).

## Rin Chat · Input

Every value Rin Chat drives, in one node. A value arrives three ways, in order of precedence:

1. **Rin Chat sends it** — replaces whatever was there.
2. **Something is connected to that field** — drag a link onto any widget and ComfyUI converts it to an input, so you can feed it from your own nodes. Used whenever Rin Chat sends nothing.
3. **Nothing else** — the value typed in the node.

So the same graph serves both masters: wire your own defaults in and Queue, and it renders them; let Rin Chat drive, and it overrides only the fields it actually has.

| Output | Type | Notes |
|---|---|---|
| `positive` / `negative` | STRING | Full prompts, styles and character prefixes already applied. |
| `width` / `height` | INT | |
| `seed` | INT | `control_after_generate` works normally for local queueing. |
| `steps` / `cfg` | INT / FLOAT | Only replaced if set on the provider in Rin Chat — otherwise your numbers stand. |
| `batch_size` | INT | Wire to your latent's batch size. Rin Chat's Image Studio drives it; chats always send 1. |
| `from_api` | BOOLEAN | `true` only when Rin Chat is driving. Wire to switches to bypass preview/save branches for API runs (and keep them for local queues). |
| `from_api_int` | INT | The same flag as 1/0, for index-style switches. |
| `project` | STRING | Free text from the Image Studio's Project field — filename prefixes, folder routing, whatever your workflow does with it. Blank = your typed value stands. |

## Rin Chat · Output

Where Rin Chat collects the picture. Behaves like Preview Image when you use ComfyUI on its own: the image shows in the node and goes to the **temp** directory, not your output folder — driving a chat shouldn't quietly fill your disk with every reroll. Add your own Save Image alongside if you want copies kept. The workflow is embedded in the PNG, so results drag back into ComfyUI like any other output.

## The `key` field

Leave it blank. It only matters if one workflow contains **more than one** Rin Chat Input — then give each a name and set the same name on the provider in Rin Chat. The key can also be fed from a string node if you prefer wiring it.

## Sample workflow

[`sample-workflows/z-image-turbo.json`](sample-workflows/z-image-turbo.json) is a complete text-to-image workflow for **Z-Image Turbo** using only core ComfyUI nodes plus the two Rin Chat nodes. Drag the file into ComfyUI to import it (it's in API format; current ComfyUI converts it to a graph on drop).

Models it expects (adjust the loader filenames to whatever you have):

- `diffusion_models/z_image_turbo_bf16.safetensors`
- `text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` (loaded as type `lumina2`)
- `vae/zImage_vae.safetensors`

Turbo is distilled: the defaults are **8 steps at CFG 1** — leave Steps/CFG blank in Rin Chat's provider settings to keep them, or set the same numbers. Press **Queue** once after importing and Rin Chat picks it up.

## How Rin Chat finds your workflow

ComfyUI records every queued prompt in its history in API format. Rin Chat reads that history and uses the **latest workflow you queued from the ComfyUI frontend** that contains these nodes — its own submissions are tagged and ignored, so it never adopts its own echo. It keeps the last known copy for when history is empty (a restart), and loading a *Save (API Format)* file in Rin Chat's settings pins that exact file instead.

Your graph is never modified beyond the values on the Rin Chat nodes themselves.

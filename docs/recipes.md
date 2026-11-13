# recipes: a chain that somebody else can use

Read off Fuser's index and two individual recipe pages on 2026-11-13 (`fuser.studio/recipes`, 198
recipes shown; PS1-Style Graphics and Adding Micrographics). This page is what a recipe is *there*, what
flowby had already, and the small part that was missing.

## what their recipe page actually contains

Their markup, in order, for PS1 Style Graphics:

```
PS1-Style Art                                  ← category
PS1-Style Subject Image                        ← a name for the RESULT, not for the process
Transform a text subject, such as "red panda", ← one line: what you bring, what you get
into a PS1-style image for character … concepts
Recipe v2   PS1 Style Graphics   PS1-Style Image ← the recipe, its version, its output
Inputs   Subject                               ← the exposed input, with a saved example
Outputs  PS1-Style Image
@maggie · v2                                   ← an author and a version
Models in this recipe: GPT Image (OpenAI)
```

Two things in that list are easy to miss and are the whole design.

**The input line is written imperatively, naming the thing you bring.** "Upload a photo of one or more
people to create an image styled with…", "Upload an object or image and receive an image showing that
object with micrographics added", "Transform a text subject… into a PS1-style image". All 198 read that
way. It is not marketing voice, it is the affordance: the sentence tells you what to have in hand before
you open the thing.

**The index is two facets over a large shelf.** 198 recipes, filtered by output type (3D, Audio, Image,
Text, Video) and by category (27 of them: Architecture & Spaces, Art & Illustration, Branding &
Identity, Character & Concept Sheets, Editorial & Publishing, Fashion & Streetwear, Film &
Entertainment, Gaming, Icon & Asset Packs, Interiors & Decor, Logos & Brand Kits, Lookbooks &
Editorials, Marketing & Advertising, Memes, Merch & Apparel, Moodboard & Collage, Moodboards & Style
Frames, Music & Album Art, Photography, Product & Industrial, Product & Packaging Mockups, Social &
Content, Stickers & Emotes, Storyboards & Comics, Templates, Toys & Collectibles, Type & Lettering,
Wallpapers & Backplates, Web & Interface, Zines & DIY). Every card carries the same shape: title,
`@author`, the imperative line, category.

## the behaviour the version number implies

From their features page, and confirmed by every recipe being `v2` rather than absent: **a placement is
pinned to the version it was placed at.** Improving a recipe does not reach into projects already using
it; you adopt an update when you decide to. Their own words: "Placed Recipes use a specific flow
version… Adopt the update when ready." And: "Some descriptive metadata, including names and labels, is
shared across versions."

That split, behaviour versus metadata, is the useful rule. A name or a label can change freely. The
wiring cannot.

## what flowby had, and what it has now

`Scene.record` already read a chain back (preset, values, slots, measured cost) and `Scene.replay`
applied it to another element, refusing a recipe recorded on a different wire. Nothing new was stored,
because the chain *was* the recipe. What was missing was everything that makes a chain usable by a
stranger: no name for the result, no version, no exposed inputs, no pin.

`src/flowby/recipes.py` adds exactly that and nothing else:

- **`version`**, six characters, hashed over the steps, their values, their slot wiring and the targets
  the exposed inputs feed. A param change moves it. A rename does not. The output's own name does not,
  because it is a label like the recipe's, and their shared-metadata rule says so. The output's *type*
  cannot change without the steps changing, since it is derived from the last step.
- **`Exposed`**, one control a stranger may change, with the step and param it feeds and the value the
  recipe was saved with. `default_inputs()` picks the first step's sweep slider when it has one, which is
  the preset's own statement of the control that matters.
- **`Placement`**, the recipe as a board holds it. `holds()` refuses once the recipe has moved on, naming
  both versions and the word *adopt*; `adopt()` is the one path that changes finished work; `view()`
  reports pin, available version and whether an update is offered without running anything.
- **`shelf()` and `facets()`**, the two facets over a list of recipes, with counts, so a filter menu need
  not guess.

The three refusals are the substance, because each one is a bug that only appears when a stranger tries
the recipe:

| refused | why it is not a warning |
| --- | --- |
| an exposed input feeding a step that is not in the chain | a control that changes nothing is a lie |
| two exposed inputs onto the same step and param | the second silently wins and the first looks broken |
| a starting value outside its own control's range | the recipe would refuse to open at its own saved value |

`bin/flowby recipe` prints every chain on the demo board as a recipe: name, version, exposed input with
its starting value and target, output, models, estimate, and the steps. `--json` emits the panel a page
would draw.

## what is still not built

- **Nothing pins a version yet.** `Placement` exists and is tested; no board placement holds one, because
  the board has no notion of a placed recipe, only a chain applied to an element.
- **The brief is checked for length, not for shape.** Refusing a brief that names none of its inputs
  would be guesswork over English, so the imperative rule is documented here and followed in the CLI's
  own briefs (`bring your own sketch and get mesh back`) rather than enforced by a regex.
- **No shelf of recipes exists.** `shelf()` and `facets()` work on a list; the demo board produces two
  chains and one of them is empty.
- **Categories are the wire kind** (`record["kind"]`) in the CLI's own recipes, not the 27-way taxonomy a
  browsing index needs.

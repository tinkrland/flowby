/** the entry the recipe render test bundles: the card drawn by the real component. */
import { RecipeCardBody } from "../src/RecipeCard";
import { cardView } from "../src/recipe.mjs";

export function RenderCard({ card, onRun }: { card: any; onRun?: () => void }) {
  const view = cardView(card);
  if (!view) return <em>no card</em>;
  return <RecipeCardBody view={view} onRun={onRun} />;
}

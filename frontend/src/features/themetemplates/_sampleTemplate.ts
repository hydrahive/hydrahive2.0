/** Beispiel-Template wie es ein Designer schreiben würde. Freies HTML/CSS fürs
 *  Aussehen, <hh-…/>-Platzhalter für die interaktiven Bausteine. Der <script>
 *  am Ende beweist das Sanitizing: er wird NICHT ausgeführt (verworfen). */
export const SAMPLE_TEMPLATE = `
<section class="rounded-2xl p-6 mb-4"
         style="background:linear-gradient(135deg,#1e1b4b,#0f172a);border:1px solid rgba(255,255,255,.08)">
  <h2 class="text-2xl font-bold text-white mb-1">Mein Designer-Theme</h2>
  <p class="text-indigo-200 text-sm">
    Alles hier ist frei gestaltetes HTML/CSS. Die Kacheln unten sind Platzhalter,
    die die App durch echte, lebende Bausteine ersetzt.
  </p>
</section>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
  <hh-tailscale/>
  <hh-agentlink/>
</div>

<div class="mt-3">
  <hh-minimax/>
</div>

<p class="text-center text-zinc-500 text-xs mt-6" style="letter-spacing:.05em">
  ✦ vom Designer gestaltet ✦
</p>

<script>alert('dieser Code darf NIEMALS laufen')</script>
`

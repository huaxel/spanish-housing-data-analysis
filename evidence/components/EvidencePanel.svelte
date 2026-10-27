<script context="module">
  export const evidenceInclude = true;
</script>

<script>
  import { onDestroy } from 'svelte';
  import { Query } from '@evidence-dev/sdk/usql';
  import provenance from './provenance.generated.json';
  import { selectRows, asCsv, saveFile } from './evidence-data.js';

  export let data;
  export let chart;
  export let columns;
  export let files;
  export let definition;
  export let coverage;

  const methods = {
    reportaje: 'docs/methods.md',
    perfil: 'docs/municipal_profile.md',
    deficit: 'docs/deficit_explainer.md',
    'comparar-municipios': 'docs/municipal_profile.md#matched-municipality-comparison'
  };
  $: method = Object.entries(methods).find(([route]) => chart.startsWith(route + '-'))?.[1];

  let rows = [];
  let sql = '';
  let loading = true;
  let error = '';
  let unsubscribe = () => {};

  function connect(query) {
    unsubscribe();
    rows = [];
    sql = '';
    error = '';
    loading = true;
    if (!Query.isQuery(query)) {
      error = 'Consulta no disponible';
      loading = false;
      return;
    }
    unsubscribe = query.subscribe(value => {
      loading = !value.dataLoaded;
      error = value.error ? 'No se pudo cargar la consulta' : '';
      rows = loading || error ? [] : Array.from(value);
      sql = query.originalText;
    });
    query.fetch();
  }
  $: connect(data);
  onDestroy(() => unsubscribe());

  $: selected = loading || error ? [] : selectRows(rows, columns);
  $: missing = columns.map(column => ({column, count: selected.filter(row => row[column] === null).length}));

  function download(format) {
    if (loading || error) return;
    const content = format === 'csv' ? asCsv(selected, columns) : JSON.stringify(selected, null, 2) + '\n';
    saveFile(`${chart}.${format}`, content, format === 'csv' ? 'text/csv;charset=utf-8' : 'application/json;charset=utf-8');
  }
</script>

<details class="evidence-panel" data-evidence-chart={chart}>
  <summary aria-label={"¿De dónde sale este gráfico? " + definition}>¿De dónde sale este gráfico?</summary>
  <div class="evidence-content">
    <p><strong>Definición.</strong> {definition}</p>
    <p><strong>Cobertura y límites.</strong> {coverage}</p>
    <p class="note">Fecha de descarga no es año de observación: los años y códigos de los datos se conservan en la descarga. No se añaden intervalos de incertidumbre ni inferencias causales.</p>
    <h4>Fuente y versión fijadas</h4>
    <ul>
      {#each files as file}
        {@const source = provenance.sources[file]}
        <li>
          <strong>{source.publisher}</strong> · descarga registrada: {source.accessed || 'sin fecha registrada'}
          {#if source.url} · <a href={source.url}>Origen publicado</a>{/if}
          <div><code>{file}</code></div>
          <div class="fingerprint">SHA-256: <code>{source.sha256}</code></div>
        </li>
      {/each}
    </ul>
    <p class="note">Versión del manifiesto de entradas: {provenance.snapshot_date}. Las huellas identifican los archivos fijados, no certifican por sí solas su interpretación.</p>
    <p class="fingerprint">Huella del manifiesto: <code>{provenance.manifest_sha256}</code></p>
    {#if loading}
      <p role="status">Actualizando datos de la selección…</p>
    {:else if error}
      <p role="alert">{error}</p>
    {:else}
      <p><strong>Filas de la consulta actual:</strong> {selected.length} (incluye filas con valores ausentes).</p>
      <p class="note">Celdas nulas por columna: {missing.map(item => `${item.column}: ${item.count}`).join(' · ')}. No se sustituyen por ceros.</p>
    {/if}
    <div class="downloads">
      <button type="button" disabled={loading || !!error} on:click={() => download('csv')}>Descargar CSV del gráfico</button>
      <button type="button" disabled={loading || !!error} on:click={() => download('json')}>Descargar JSON del gráfico</button>
    </div>
    <p class="note">Se descargan las columnas indicadas, con su precisión original, sin formato visual ni filas de otras selecciones. CSV deja vacíos los nulos; JSON conserva <code>null</code>. CSV protege textos que podrían ejecutarse como fórmulas; JSON conserva el texto original.</p>
    <h4>Consulta resuelta del gráfico</h4>
    <p class="note">Es la consulta de la página con la selección actual, no una copia mantenida aparte. Las tablas <code>housing</code>, <code>access</code> y los demás espacios de fuentes corresponden a las exportaciones SQL del repositorio.</p>
    <pre><code>{sql}</code></pre>
    <p><a href={"https://github.com/huaxel/spanish-housing-data-analysis/blob/main/" + method}>Método e implementación</a> · <a href="https://github.com/huaxel/spanish-housing-data-analysis/tree/main/evidence/sources">Exportaciones SQL de las fuentes</a> · <a href="https://github.com/huaxel/spanish-housing-data-analysis/blob/main/data/input_manifest.json">Manifiesto de entradas</a></p>
  </div>
</details>

<style>
  .evidence-panel { margin: .5rem 0 1.5rem; border: 1px solid #94a3b8; border-radius: .4rem; font-size: .9rem; }
  summary { cursor: pointer; padding: .65rem .8rem; font-weight: 600; }
  .evidence-content { padding: 0 .8rem .8rem; min-width: 0; }
  p { margin: .65rem 0; }
  h4 { font-weight: 600; margin: 1rem 0 .5rem; }
  li { margin: .6rem 0; }
  .note { font-size: .85rem; }
  code { overflow-wrap: anywhere; }
  pre { max-width: 100%; white-space: pre-wrap; overflow-wrap: anywhere; padding: .6rem; background: color-mix(in srgb, currentColor 5%, transparent); }
  .fingerprint { font-size: .8rem; }
  .downloads { display: flex; gap: .6rem; flex-wrap: wrap; }
  button { padding: .5rem .7rem; border: 1px solid currentColor; border-radius: .3rem; cursor: pointer; }
  button:disabled { opacity: .5; cursor: wait; }
</style>

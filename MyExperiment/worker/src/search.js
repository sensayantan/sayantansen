// Retrieval: embed the visitor's question, compare it against every stored
// document vector, return the best matches.
//
// There is no vector database here, deliberately. 1900 vectors of 384
// dimensions is 2.8 MB — small enough to hold in memory and compare by brute
// force in well under a millisecond. A managed vector DB earns its keep at a
// scale this corpus is nowhere near, and would add a paid dependency to
// something that currently costs nothing.

// The Workers AI model must be the same one that built index.pkl, or the
// query lands in a different vector space than the documents and every score
// is meaningless — while still looking like a plausible number. docs.json
// carries the name the index was built with; loadIndex() checks it.
const EMBEDDING_MODEL = "@cf/baai/bge-small-en-v1.5";
const EXPECTED_LOCAL_MODEL = "BAAI/bge-small-en-v1.5";

// calibrate.py measured this corpus locally: unrelated questions peaked at
// 0.586, real ones started at 0.712, so the floor sat at 0.63.
//
// Workers AI scores the same corpus lower. On "is autism genetic" the top
// result is 0.742 here against 0.812 locally, and on the weakest prepared
// question the four results came back at 0.648 / 0.638 / 0.635 / 0.632 —
// the last of them clearing 0.63 by two thousandths. Those are the right
// papers; a marginally weaker question would have returned an empty page.
//
// 0.56 holds the same position in the Worker's range that 0.63 held
// locally, after shifting by the ~0.065 offset measured on identical
// questions.
const MIN_SCORE = 0.56;

// A Worker isolate is reused across requests, so the index loads once and
// then stays hot. The promise (not the value) is cached so concurrent first
// requests share one load rather than each starting their own.
let indexPromise = null;

async function fetchAsset(env, path) {
  // env.ASSETS.fetch needs a well-formed URL; the origin is ignored.
  const response = await env.ASSETS.fetch(new Request(`https://assets.local/${path}`));
  if (!response.ok) throw new Error(`Could not load ${path} (${response.status})`);
  return response;
}

function loadIndex(env) {
  if (!indexPromise) {
    indexPromise = (async () => {
      const [metaResponse, vectorResponse] = await Promise.all([
        fetchAsset(env, "worker-index/docs.json"),
        fetchAsset(env, "worker-index/vectors.bin"),
      ]);
      const meta = await metaResponse.json();
      const buffer = await vectorResponse.arrayBuffer();
      const vectors = new Float32Array(buffer);

      const expected = meta.count * meta.dims;
      if (vectors.length !== expected) {
        throw new Error(
          `vectors.bin holds ${vectors.length} floats, docs.json implies ${expected} — ` +
            "the two files are out of step; re-run export_worker_index.py"
        );
      }
      if (meta.model !== EXPECTED_LOCAL_MODEL) {
        throw new Error(
          `Index was built with ${meta.model}, but this Worker embeds queries with ` +
            `${EMBEDDING_MODEL}. Those must be the same model.`
        );
      }
      return { ...meta, vectors };
    })().catch((error) => {
      // Don't cache a failure — a transient asset fetch shouldn't poison the
      // isolate for every later request.
      indexPromise = null;
      throw error;
    });
  }
  return indexPromise;
}

async function embedQuery(env, text) {
  const result = await env.AI.run(EMBEDDING_MODEL, { text: [text] });
  const vector = result?.data?.[0];
  if (!Array.isArray(vector)) throw new Error("Embedding model returned no vector");

  // The stored vectors are unit length, so normalising here makes the dot
  // product below exactly cosine similarity. Workers AI may already return
  // normalised vectors; doing it anyway costs nothing and removes the
  // assumption.
  let norm = 0;
  for (const value of vector) norm += value * value;
  norm = Math.sqrt(norm) || 1;
  return Float32Array.from(vector, (value) => value / norm);
}

export async function search(env, question, topK) {
  const index = await loadIndex(env);
  const query = await embedQuery(env, (index.query_prefix || "") + question);

  if (query.length !== index.dims) {
    throw new Error(`Query has ${query.length} dimensions, index has ${index.dims}`);
  }

  // Partial selection rather than sorting all 1900: we only ever want a
  // handful, and topK is small enough that the insertion scan is cheaper
  // than a full sort.
  const best = [];
  for (let row = 0; row < index.count; row++) {
    const offset = row * index.dims;
    let score = 0;
    for (let d = 0; d < index.dims; d++) score += query[d] * index.vectors[offset + d];
    if (score < MIN_SCORE) continue;
    if (best.length < topK || score > best[best.length - 1].score) {
      best.push({ score, doc: index.docs[row] });
      best.sort((a, b) => b.score - a.score);
      if (best.length > topK) best.pop();
    }
  }
  return best;
}

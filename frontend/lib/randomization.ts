export type ConditionCode = "A" | "B";

export type RandomizationPreview = {
  sequence: ConditionCode[];
  perCondition: { a: number; b: number };
  imbalance: number;
  seedHash: number;
  blocks: number;
  blockLength: number;
};

export type RandomizationInput = {
  seed: string;
  blocks: number;
  blockLength: number;
  scheme: "block" | "counterbalance";
};

export function fnv1a(value: string): number {
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return hash >>> 0;
}

export function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffle<T>(items: T[], random: () => number): T[] {
  const copy = [...items];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(random() * (index + 1));
    [copy[index], copy[swap]] = [copy[swap], copy[index]];
  }
  return copy;
}

export function buildRandomizationPreview(input: RandomizationInput): RandomizationPreview {
  const blocks = clampInteger(input.blocks, 1, 50);
  const blockLength = clampInteger(input.blockLength, 1, 20);
  const seedHash = fnv1a(`${input.seed}|${blocks}|${blockLength}|${input.scheme}`);
  const random = mulberry32(seedHash);
  const sequence: ConditionCode[] = [];

  for (let block = 0; block < blocks; block += 1) {
    const base: ConditionCode[] = [
      ...Array.from({ length: blockLength }, () => "A" as const),
      ...Array.from({ length: blockLength }, () => "B" as const),
    ];
    if (input.scheme === "counterbalance") {
      const ordered = block % 2 === 0 ? base : [...base].reverse();
      sequence.push(...ordered);
    } else {
      sequence.push(...shuffle(base, random));
    }
  }

  const a = sequence.filter((condition) => condition === "A").length;
  const b = sequence.length - a;
  return {
    sequence,
    perCondition: { a, b },
    imbalance: Math.abs(a - b),
    seedHash,
    blocks,
    blockLength,
  };
}

function clampInteger(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, Math.trunc(value)));
}

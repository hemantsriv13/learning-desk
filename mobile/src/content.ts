// The curriculum, exported from the desktop app by tools/export_mobile.py. Do not edit content.json by hand.
import raw from '../assets/content.json';

export type Figure = { title: string; svg: string; notice: string };
export type Section = {
  id: string; title: string; body: string; callout: string; code: string;
  table: { columns: string[]; rows: string[][] } | null; figure: Figure | null; interactive: boolean;
};
export type Check = { id: string; prompt: string; options: string[]; answer: string; explanation: string; section: string };
export type Lesson = {
  id: string; title: string; topic: string; minutes: number; level: string; summary: string; objective: string;
  intro: string; keyIdeas: string[]; sections: Section[]; activity: { title: string; steps: string[] };
  checks: Check[]; version: string;
};
export type Item = { id: string; kind: 'lesson' | 'outline'; title: string; objective: string; planned: string[] };
export type Topic = {
  id: string; number: number; title: string; blurb: string; why: string; track: string; thumb: string; items: Item[];
};
export type Track = { name: string; hue: string; icon: string };

const content = raw as unknown as {
  tracks: Track[]; topics: Topic[]; lessons: Record<string, Lesson>; art: Record<string, string>;
};

export const TRACKS = content.tracks;
export const TOPICS = content.topics;
export const LESSONS = content.lessons;
export const ART = content.art;
export const TOPIC_BY_ID: Record<string, Topic> = Object.fromEntries(TOPICS.map((t) => [t.id, t]));
export const HUE: Record<string, string> = Object.fromEntries(TRACKS.map((t) => [t.name, t.hue]));
/** Finished lessons in map order: topic by topic, as on the desktop Explore page. */
export const ORDERED: Lesson[] = TOPICS.flatMap((t) => t.items.filter((i) => i.kind === 'lesson').map((i) => LESSONS[i.id]));

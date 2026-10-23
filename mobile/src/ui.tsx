// Theme and shared building blocks. Same look as the desktop app: black page, graphite cards with a visible
// edge, mint for progress and the one main action, Space Grotesk headings and Inter text.
import { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, TextStyle, View, ViewStyle, useWindowDimensions } from 'react-native';
import { SvgXml } from 'react-native-svg';

export const C = {
  ground: '#050505', card: '#2a2a2a', raised: '#353535', edge: '#5a5a5a', rule: '#444444',
  text: '#f4f4f4', muted: '#c8c8c8', faint: '#aaaaaa', mint: '#3ddc97', mintDark: '#22a06b', amber: '#ffb347',
};
// Spacing scale in density-independent points (React Native has no rem; text follows the phone's font size).
export const SP = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 };
export const F = { head: 'SpaceGrotesk_700Bold', headSemi: 'SpaceGrotesk_600SemiBold', body: 'Inter_400Regular', bodySemi: 'Inter_600SemiBold' };

export function Card({ children, hue, style }: { children: ReactNode; hue?: string; style?: ViewStyle }) {
  return (
    <View style={[s.card, hue ? { borderColor: hue + '88', borderTopColor: hue, borderTopWidth: 2 } : null, style]}>
      {children}
    </View>
  );
}

export function H1({ children }: { children: ReactNode }) {
  return <Text style={s.h1} accessibilityRole="header">{children}</Text>;
}
export function H2({ children, style }: { children: ReactNode; style?: TextStyle }) {
  return <Text style={[s.h2, style]} accessibilityRole="header">{children}</Text>;
}
export function Muted({ children, style }: { children: ReactNode; style?: TextStyle }) {
  return <Text style={[s.muted, style]}>{children}</Text>;
}

export function Button({ label, onPress, primary, small }: { label: string; onPress: () => void; primary?: boolean; small?: boolean }) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      style={({ pressed }) => [s.btn, primary ? s.btnPrimary : s.btnSecondary, small && s.btnSmall, pressed && { opacity: 0.75 }]}
    >
      <Text style={[s.btnText, primary && { color: C.ground }]}>{label}</Text>
    </Pressable>
  );
}

export function Chip({ label, active, hue, onPress }: { label: string; active: boolean; hue?: string; onPress: () => void }) {
  const tint = hue ?? C.mint;
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      style={[s.chip, active && { backgroundColor: tint + '33', borderColor: tint }]}
    >
      <Text style={[s.chipText, active && { color: C.text }]}>{label}</Text>
    </Pressable>
  );
}

/** Pixel art or a diagram from content.json, scaled to `width`, keeping the SVG's aspect ratio. */
export function Art({ xml, width }: { xml: string; width: number }) {
  const box = /viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"/.exec(xml);
  const ratio = box ? Number(box[2]) / Number(box[1]) : 0.6;
  return <SvgXml xml={xml} width={width} height={Math.round(width * ratio)} />;
}

/** Full-width figure inside the screen's padding. */
export function Figure({ xml }: { xml: string }) {
  const { width } = useWindowDimensions();
  return <Art xml={xml} width={Math.min(width - 64, 640)} />;
}

export function Bar({ value, hue = C.mint }: { value: number; hue?: string }) {
  return (
    <View style={s.track} accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: Math.round(value * 100) }}>
      <View style={[s.fill, { width: `${Math.max(0, Math.min(1, value)) * 100}%`, backgroundColor: hue }]} />
    </View>
  );
}

// ---- A small renderer for the lesson Markdown: paragraphs, bullet and numbered lists, **bold** and `code`.
function Inline({ text, style }: { text: string; style?: TextStyle }) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean);
  return (
    <Text style={[s.body, style]}>
      {parts.map((p, i) =>
        p.startsWith('**') ? <Text key={i} style={{ fontFamily: F.bodySemi, color: C.text }}>{p.slice(2, -2)}</Text>
        : p.startsWith('`') ? <Text key={i} style={s.code}>{p.slice(1, -1)}</Text>
        : p.replace(/\*([^*]+)\*/g, '$1'))}
    </Text>
  );
}

export function Md({ text }: { text: string }) {
  const blocks = text.trim().split(/\n\s*\n/);
  return (
    <View style={s.blocks}>
      {blocks.map((block, i) => {
        const lines = block.split('\n');
        if (lines.every((l) => /^\s*([-*]|\d+\.)\s/.test(l))) {
          return (
            <View key={i} style={s.list}>
              {lines.map((l, j) => {
                const m = /^\s*([-*]|\d+\.)\s+(.*)$/.exec(l)!;
                return (
                  <View key={j} style={s.listRow}>
                    <Text style={[s.body, { color: C.mint }]}>{m[1] === '-' || m[1] === '*' ? '•' : m[1]}</Text>
                    <View style={s.grow}><Inline text={m[2]} /></View>
                  </View>
                );
              })}
            </View>
          );
        }
        return <Inline key={i} text={lines.join(' ')} />;
      })}
    </View>
  );
}

export const s = StyleSheet.create({
  blocks: { gap: SP.md },
  list: { gap: SP.sm },
  listRow: { flexDirection: 'row', gap: SP.sm },
  grow: { flex: 1 },
  card: { backgroundColor: C.card, borderColor: C.edge, borderWidth: 1, borderRadius: 16, padding: 16, gap: 10 },
  h1: { fontFamily: F.head, fontSize: 28, color: C.text, letterSpacing: -0.3 },
  h2: { fontFamily: F.headSemi, fontSize: 18, color: C.text },
  body: { fontFamily: F.body, fontSize: 16, lineHeight: 25, color: C.text },
  muted: { fontFamily: F.body, fontSize: 14, lineHeight: 20, color: C.muted },
  code: { fontFamily: 'monospace', fontSize: 14, color: C.mint, backgroundColor: '#1c1c1c' },
  btn: { borderRadius: 999, paddingHorizontal: 18, minHeight: 48, justifyContent: 'center', alignSelf: 'flex-start' },
  btnSmall: { minHeight: 44, paddingHorizontal: 14 },
  btnPrimary: { backgroundColor: C.mint },
  btnSecondary: { borderWidth: 1, borderColor: C.edge },
  btnText: { fontFamily: F.bodySemi, fontSize: 15, color: C.text },
  chip: { borderWidth: 1, borderColor: C.edge, borderRadius: 999, paddingHorizontal: 14, minHeight: 40, justifyContent: 'center' },
  chipText: { fontFamily: F.bodySemi, fontSize: 13, color: C.muted },
  track: { height: 8, borderRadius: 4, backgroundColor: C.rule, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: 4 },
});

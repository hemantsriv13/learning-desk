// The app's screens. Navigation is a small stack kept in App.tsx; `nav` pushes, pops and switches tabs.
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import { ART, HUE, LESSONS, Lesson, ORDERED, TOPICS, TOPIC_BY_ID, TRACKS } from './content';
import { openLesson, useApp } from './store';
import { Art, Bar, Button, C, Card, Chip, F, Figure, H1, H2, Md, Muted, SP, s as ui } from './ui';

export type Route =
  | { name: 'home' } | { name: 'explore'; track?: string } | { name: 'notes' }
  | { name: 'topic'; id: string } | { name: 'lesson'; id: string };
export type Nav = { push: (r: Route) => void; pop: () => void; tab: (r: Route) => void };

function Screen({ children }: { children: React.ReactNode }) {
  return <ScrollView style={st.screen} contentContainerStyle={st.content}>{children}</ScrollView>;
}

function Back({ nav, label }: { nav: Nav; label: string }) {
  return (
    <Pressable onPress={nav.pop} accessibilityRole="button" style={st.back}>
      <Text style={st.backText}>← {label}</Text>
    </Pressable>
  );
}

const trackOf = (lesson: Lesson) => TOPIC_BY_ID[lesson.topic].track;

// ---------------------------------------------------------------- Home
export function Home({ nav }: { nav: Nav }) {
  const store = useApp();
  const { progress, current } = store.state;
  const [shift, setShift] = useState(0);
  const now = new Date();
  const part = now.getHours() < 12 ? 'morning' : now.getHours() < 18 ? 'afternoon' : 'evening';
  const night = now.getHours() < 6 || now.getHours() >= 18;
  const done = ORDERED.filter((l) => progress[l.id]?.status === 'completed').length;
  const started = ORDERED.filter((l) => progress[l.id]?.status === 'started').length;
  const lesson = current ? LESSONS[current] : null;
  const ideas = ORDERED.flatMap((l) => l.keyIdeas.map((idea) => ({ lesson: l, idea })));
  const day = Math.floor(now.getTime() / 86_400_000);
  const pick = ideas[(day * 7 + shift) % ideas.length];
  const next = ORDERED.filter((l) => l.id !== current && progress[l.id]?.status !== 'completed').slice(0, 3);
  const open = (id: string) => { openLesson(store, id); nav.push({ name: 'lesson', id }); };

  return (
    <Screen>
      <View style={st.headerRow}>
        <View style={ui.grow}>
          <H1>Good {part}</H1>
          <Muted>{done} of {ORDERED.length} lessons completed</Muted>
        </View>
        <Art xml={night ? ART.deskNight : ART.deskDay} width={120} />
      </View>

      <Card hue={C.mint}>
        <Muted>{lesson ? 'Pick up where you left off' : 'Start here'}</Muted>
        <H2>{(lesson ?? ORDERED[0]).title}</H2>
        <Muted>{TOPIC_BY_ID[(lesson ?? ORDERED[0]).topic].title} · {(lesson ?? ORDERED[0]).minutes} min</Muted>
        {lesson && <Bar value={((progress[lesson.id]?.section ?? 0) + 1) / lesson.sections.length} />}
        <Button primary label={lesson ? 'Continue learning' : 'Start the first lesson'} onPress={() => open((lesson ?? ORDERED[0]).id)} />
      </Card>

      <Card>
        <H2>Your progress</H2>
        <Bar value={done / ORDERED.length} />
        <Muted>{done} completed · {started} in progress · {ORDERED.length - done - started} not started</Muted>
      </Card>

      <Card hue={C.amber}>
        <Muted>Idea of the day · from {pick.lesson.title}</Muted>
        <Text style={st.idea}>{pick.idea}</Text>
        <View style={st.row}>
          <Button small label="Open the lesson" onPress={() => open(pick.lesson.id)} />
          <Button small label="Another idea" onPress={() => setShift(shift + 1)} />
        </View>
      </Card>

      <H2 style={st.section}>Explore by track</H2>
      <View style={st.grid}>
        {TRACKS.map((t) => {
          const topics = TOPICS.filter((x) => x.track === t.name);
          const ready = topics.reduce((n, x) => n + x.items.filter((i) => i.kind === 'lesson').length, 0);
          return (
            <Pressable key={t.name} accessibilityRole="button" style={[st.tile, { borderTopColor: t.hue }]}
              onPress={() => nav.tab({ name: 'explore', track: t.name })}>
              <Art xml={t.icon} width={42} />
              <Text style={st.tileTitle}>{t.name}</Text>
              <Muted>{topics.length} topics · {ready ? `${ready} lessons` : 'planned'}</Muted>
            </Pressable>
          );
        })}
      </View>

      {next.length > 0 && <H2 style={st.section}>Next up</H2>}
      {next.map((l) => (
        <Pressable key={l.id} onPress={() => open(l.id)} accessibilityRole="button">
          <Card hue={HUE[trackOf(l)]}>
            <Text style={st.cardTitle}>{l.title}</Text>
            <Muted>{TOPIC_BY_ID[l.topic].title} · {l.minutes} min · {l.level}</Muted>
          </Card>
        </Pressable>
      ))}
    </Screen>
  );
}

// ---------------------------------------------------------------- Explore
export function Explore({ nav, track }: { nav: Nav; track?: string }) {
  const [chosen, setChosen] = useState<string | undefined>(track);
  const shown = TRACKS.filter((t) => !chosen || t.name === chosen);
  return (
    <Screen>
      <View style={st.headerRow}>
        <View style={ui.grow}>
          <H1>Explore</H1>
          <Muted>{TOPICS.length} topics · {ORDERED.length} lessons ready</Muted>
        </View>
        <Art xml={ART.explore} width={112} />
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={st.chips}>
        <Chip label="All" active={!chosen} onPress={() => setChosen(undefined)} />
        {TRACKS.map((t) => (
          <Chip key={t.name} label={t.name} hue={t.hue} active={chosen === t.name} onPress={() => setChosen(t.name)} />
        ))}
      </ScrollView>
      {shown.map((t) => (
        <View key={t.name} style={st.group}>
          <View style={st.trackHead}>
            <Art xml={t.icon} width={28} />
            <H2>{t.name}</H2>
          </View>
          {TOPICS.filter((x) => x.track === t.name).map((topic) => {
            const ready = topic.items.filter((i) => i.kind === 'lesson').length;
            return (
              <Pressable key={topic.id} onPress={() => nav.push({ name: 'topic', id: topic.id })} accessibilityRole="button">
                <Card hue={t.hue}>
                  <Text style={st.cardTitle}>{topic.number}. {topic.title}</Text>
                  <Muted>{topic.blurb}</Muted>
                  <Muted style={st.small}>{ready ? `${ready} lessons ready` : `${topic.items.length} planned lessons · not written yet`}</Muted>
                </Card>
              </Pressable>
            );
          })}
        </View>
      ))}
    </Screen>
  );
}

// ---------------------------------------------------------------- Topic
export function TopicScreen({ nav, id }: { nav: Nav; id: string }) {
  const store = useApp();
  const topic = TOPIC_BY_ID[id];
  const hue = HUE[topic.track];
  const ready = topic.items.some((i) => i.kind === 'lesson');
  return (
    <Screen>
      <Back nav={nav} label="Back" />
      <Muted>Topic {topic.number} · {topic.track}</Muted>
      <H1>{topic.title}</H1>
      <Muted>{topic.blurb}</Muted>
      {!ready && (
        <View style={st.row}>
          <Art xml={ART.robot} width={66} />
          <Muted style={ui.grow}>Still being built. These lessons are outlines of what each will cover.</Muted>
        </View>
      )}
      {topic.items.map((item) => {
        const status = store.state.progress[item.id]?.status;
        return item.kind === 'lesson' ? (
          <Card key={item.id} hue={hue}>
            <Muted style={st.small}>{status === 'completed' ? 'Completed' : status === 'started' ? 'In progress' : 'Ready'}</Muted>
            <Text style={st.cardTitle}>{item.title}</Text>
            <Muted>{item.objective}</Muted>
            <Button small primary={!status} label={status ? 'Continue' : 'Open lesson'}
              onPress={() => { openLesson(store, item.id); nav.push({ name: 'lesson', id: item.id }); }} />
          </Card>
        ) : (
          <Card key={item.id} style={st.outline}>
            <Muted style={st.small}>Outline · not written yet</Muted>
            <Text style={st.cardTitle}>{item.title}</Text>
            <Muted>{item.objective}</Muted>
            {item.planned.map((p) => <Muted key={p} style={st.small}>• {p}</Muted>)}
          </Card>
        );
      })}
    </Screen>
  );
}

// ---------------------------------------------------------------- Lesson
const VIEWS = ['Overview', 'Read', 'Check', 'Notes'] as const;

export function LessonScreen({ nav, id }: { nav: Nav; id: string }) {
  const store = useApp();
  const lesson = LESSONS[id];
  const hue = HUE[trackOf(lesson)];
  const [view, setView] = useState<(typeof VIEWS)[number]>('Overview');
  const place = store.state.progress[id] ?? { status: 'started' as const, section: 0 };
  const setSection = (section: number) =>
    store.update((s) => ({ ...s, progress: { ...s.progress, [id]: { ...place, section } } }));

  return (
    <Screen>
      <Back nav={nav} label={TOPIC_BY_ID[lesson.topic].title} />
      <H1>{lesson.title}</H1>
      <Muted>{lesson.minutes} min · {lesson.level}{place.status === 'completed' ? ' · Completed' : ''}</Muted>
      <View style={st.chipsWrap}>
        {VIEWS.map((v) => <Chip key={v} label={v} hue={hue} active={view === v} onPress={() => setView(v)} />)}
      </View>
      {view === 'Overview' && <Overview lesson={lesson} hue={hue} start={() => setView('Read')} />}
      {view === 'Read' && <Read lesson={lesson} index={Math.min(place.section, lesson.sections.length - 1)}
        hue={hue} go={setSection} toCheck={() => setView('Check')} />}
      {view === 'Check' && <Quiz lesson={lesson} hue={hue} nav={nav} />}
      {view === 'Notes' && <Notes lesson={lesson} />}
    </Screen>
  );
}

function Overview({ lesson, hue, start }: { lesson: Lesson; hue: string; start: () => void }) {
  return (
    <View style={st.stack}>
      <Card hue={hue}>
        <Muted>Learning objective</Muted>
        <Text style={ui.body}>{lesson.objective}</Text>
      </Card>
      <Md text={lesson.intro} />
      <H2>Key ideas</H2>
      <Md text={lesson.keyIdeas.map((k) => `- ${k}`).join('\n')} />
      <Card>
        <H2>{lesson.activity.title}</H2>
        <Md text={lesson.activity.steps.map((step, i) => `${i + 1}. ${step}`).join('\n')} />
      </Card>
      <Button primary label="Start reading" onPress={start} />
    </View>
  );
}

function Read({ lesson, index, hue, go, toCheck }:
  { lesson: Lesson; index: number; hue: string; go: (i: number) => void; toCheck: () => void }) {
  const sec = lesson.sections[index];
  const last = index === lesson.sections.length - 1;
  return (
    <View style={st.stack}>
      <Muted>Section {index + 1} of {lesson.sections.length}</Muted>
      <Bar value={(index + 1) / lesson.sections.length} hue={hue} />
      <H2>{sec.title}</H2>
      <Md text={sec.body} />
      {sec.figure && (
        <Card>
          <Text style={st.cardTitle}>{sec.figure.title}</Text>
          <Figure xml={sec.figure.svg} />
          <Muted>What to notice: {sec.figure.notice}</Muted>
        </Card>
      )}
      {sec.interactive && <Muted>This section has an interactive example in the desktop app.</Muted>}
      {sec.table && (
        <Card>
          {sec.table.rows.map((row, r) => (
            <View key={r} style={st.tableRow}>
              {row.map((cell, c) => (
                <View key={c} style={st.tableCell}>
                  <Muted style={st.small}>{sec.table!.columns[c]}</Muted>
                  <Text style={ui.body}>{cell}</Text>
                </View>
              ))}
            </View>
          ))}
        </Card>
      )}
      {!!sec.code && (
        <ScrollView horizontal style={st.codeBox}>
          <Text style={ui.code}>{sec.code}</Text>
        </ScrollView>
      )}
      {!!sec.callout && <Card hue={C.amber}><Text style={ui.body}>{sec.callout}</Text></Card>}
      <View style={st.row}>
        {index > 0 && <Button small label="Previous" onPress={() => go(index - 1)} />}
        <Button small primary label={last ? 'Go to the quick check' : 'Next section'} onPress={() => (last ? toCheck() : go(index + 1))} />
      </View>
    </View>
  );
}

function Quiz({ lesson, hue, nav }: { lesson: Lesson; hue: string; nav: Nav }) {
  const store = useApp();
  const answers = store.state.answers[lesson.id] ?? {};
  const [pos, setPos] = useState(0);
  const done = store.state.progress[lesson.id]?.status === 'completed';
  const nextLesson = ORDERED.slice(ORDERED.indexOf(lesson) + 1).find((l) => store.state.progress[l.id]?.status !== 'completed');
  const answer = (checkId: string, option: string) =>
    store.update((s) => ({ ...s, answers: { ...s.answers, [lesson.id]: { ...answers, [checkId]: option } } }));
  const complete = () =>
    store.update((s) => ({ ...s, progress: { ...s.progress, [lesson.id]: { status: 'completed', section: s.progress[lesson.id]?.section ?? 0 } } }));

  if (pos >= lesson.checks.length) {
    const right = lesson.checks.filter((c) => answers[c.id] === c.answer).length;
    return (
      <View style={st.stack}>
        <Card hue={hue}>
          <View style={st.row}>
            <Art xml={ART.trophy} width={66} />
            <View style={ui.grow}>
              <H2>{right} of {lesson.checks.length} correct</H2>
              <Muted>{done ? 'Lesson complete.' : 'Mark the lesson complete when you are ready.'}</Muted>
            </View>
          </View>
          <View style={st.row}>
            {!done && <Button small primary label="Mark complete" onPress={complete} />}
            <Button small label="Try again" onPress={() => setPos(0)} />
          </View>
        </Card>
        {nextLesson && (
          <Button label={`Next: ${nextLesson.title}`} primary={done}
            onPress={() => { openLesson(store, nextLesson.id); nav.pop(); nav.push({ name: 'lesson', id: nextLesson.id }); }} />
        )}
      </View>
    );
  }

  const check = lesson.checks[pos];
  const chosen = answers[check.id];
  return (
    <View style={st.stack}>
      <Muted>Question {pos + 1} of {lesson.checks.length}</Muted>
      <Bar value={pos / lesson.checks.length} hue={hue} />
      <H2>{check.prompt}</H2>
      {check.options.map((o) => {
        const isAnswer = o === check.answer;
        const picked = o === chosen;
        return (
          <Pressable key={o} onPress={() => !chosen && answer(check.id, o)} accessibilityRole="radio"
            accessibilityState={{ checked: picked }}
            style={[st.option, chosen && isAnswer && st.optionRight, picked && !isAnswer && st.optionWrong]}>
            <Text style={ui.body}>{o}</Text>
          </Pressable>
        );
      })}
      {chosen && (
        <Card hue={chosen === check.answer ? C.mint : '#ff7e6b'}>
          <Text style={st.cardTitle}>{chosen === check.answer ? 'Yes.' : `Not quite: the answer is “${check.answer}”.`}</Text>
          <Muted>{check.explanation}</Muted>
        </Card>
      )}
      <View style={st.row}>
        {chosen && <Button small primary label={pos < lesson.checks.length - 1 ? 'Next question' : 'See result'} onPress={() => setPos(pos + 1)} />}
        {chosen && (
          <Button small label="Answer again" onPress={() =>
            store.update((s) => { const a = { ...answers }; delete a[check.id]; return { ...s, answers: { ...s.answers, [lesson.id]: a } }; })} />
        )}
      </View>
    </View>
  );
}

function Notes({ lesson }: { lesson: Lesson }) {
  const store = useApp();
  return (
    <View style={st.stack}>
      <Muted>Saved on this phone as you type. Never sent anywhere.</Muted>
      <TextInput
        multiline
        value={store.state.notes[lesson.id] ?? ''}
        onChangeText={(text) => store.update((s) => ({ ...s, notes: { ...s.notes, [lesson.id]: text } }))}
        placeholder="Questions, examples, connections…"
        placeholderTextColor={C.faint}
        accessibilityLabel={`Notes on ${lesson.title}`}
        style={st.input}
      />
    </View>
  );
}

// ---------------------------------------------------------------- Notes tab
export function NotesTab({ nav }: { nav: Nav }) {
  const store = useApp();
  const written = ORDERED.filter((l) => (store.state.notes[l.id] ?? '').trim());
  return (
    <Screen>
      <View style={st.headerRow}>
        <View style={ui.grow}>
          <H1>Notes</H1>
          <Muted>Everything you wrote beside a lesson</Muted>
        </View>
        <Art xml={ART.notebook} width={112} />
      </View>
      {written.length === 0 && (
        <View style={st.row}>
          <Art xml={ART.cat} width={72} />
          <Muted style={ui.grow}>Notes you write beside a lesson appear here.</Muted>
        </View>
      )}
      {written.map((l) => (
        <Pressable key={l.id} accessibilityRole="button" onPress={() => { openLesson(store, l.id); nav.push({ name: 'lesson', id: l.id }); }}>
          <Card hue={HUE[trackOf(l)]}>
            <Text style={st.cardTitle}>{l.title}</Text>
            <Muted>{store.state.notes[l.id].trim().slice(0, 160)}</Muted>
          </Card>
        </Pressable>
      ))}
    </Screen>
  );
}

const st = StyleSheet.create({
  screen: { flex: 1, backgroundColor: C.ground },
  content: { padding: SP.lg, paddingBottom: SP.xl * 3, gap: SP.md },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: SP.md, marginBottom: SP.sm },
  row: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: SP.sm },
  stack: { gap: SP.md },
  section: { marginTop: SP.md },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: SP.md },
  tile: { width: '47%', flexGrow: 1, backgroundColor: C.card, borderWidth: 1, borderColor: C.edge, borderTopWidth: 2,
    borderRadius: 14, padding: SP.md, gap: SP.xs },
  tileTitle: { fontFamily: F.headSemi, fontSize: 15, color: C.text },
  cardTitle: { fontFamily: F.headSemi, fontSize: 16, color: C.text },
  idea: { fontFamily: F.headSemi, fontSize: 19, lineHeight: 27, color: C.text },
  small: { fontSize: 13 },
  chips: { gap: SP.sm, paddingVertical: SP.xs },
  chipsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: SP.sm },
  group: { gap: SP.md, marginTop: SP.md },
  trackHead: { flexDirection: 'row', alignItems: 'center', gap: SP.sm },
  back: { minHeight: 44, justifyContent: 'center', alignSelf: 'flex-start' },
  backText: { fontFamily: F.bodySemi, fontSize: 15, color: C.mint },
  outline: { backgroundColor: 'transparent', borderStyle: 'dashed' },
  option: { borderWidth: 1, borderColor: C.edge, borderRadius: 12, padding: SP.md, minHeight: 48, backgroundColor: C.card },
  optionRight: { borderColor: C.mint, backgroundColor: '#163d2c' },
  optionWrong: { borderColor: '#ff7e6b', backgroundColor: '#3d1c17' },
  input: { minHeight: 220, textAlignVertical: 'top', backgroundColor: C.card, borderWidth: 1, borderColor: C.edge,
    borderRadius: 14, padding: SP.md, color: C.text, fontFamily: F.body, fontSize: 16 },
  codeBox: { backgroundColor: '#1c1c1c', borderRadius: 12, padding: SP.md },
  tableRow: { borderBottomWidth: 1, borderBottomColor: C.rule, paddingVertical: SP.sm, gap: SP.xs },
  tableCell: { gap: 2 },
});

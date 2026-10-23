// Learning Desk for Android: fonts, saved state, a small screen stack and the bottom tabs.
import { Inter_400Regular, Inter_600SemiBold, useFonts } from '@expo-google-fonts/inter';
import { SpaceGrotesk_600SemiBold, SpaceGrotesk_700Bold } from '@expo-google-fonts/space-grotesk';
import { StatusBar } from 'expo-status-bar';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, BackHandler, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

import { Explore, Home, LessonScreen, Nav, NotesTab, Route, TopicScreen } from './src/screens';
import { StoreContext, useStore } from './src/store';
import { C, F, SP } from './src/ui';

const TABS: { label: string; route: Route }[] = [
  { label: 'Home', route: { name: 'home' } },
  { label: 'Explore', route: { name: 'explore' } },
  { label: 'Notes', route: { name: 'notes' } },
];

export default function App() {
  const [fontsLoaded] = useFonts({ Inter_400Regular, Inter_600SemiBold, SpaceGrotesk_600SemiBold, SpaceGrotesk_700Bold });
  const store = useStore();
  const [stack, setStack] = useState<Route[]>([{ name: 'home' }]);

  const nav: Nav = useMemo(() => ({
    push: (r) => setStack((s) => [...s, r]),
    pop: () => setStack((s) => (s.length > 1 ? s.slice(0, -1) : s)),
    tab: (r) => setStack([r]),
  }), []);

  // Android back button: go back a screen; on a tab's first screen, let Android close the app.
  const onBack = useCallback(() => {
    if (stack.length > 1) { nav.pop(); return true; }
    return false;
  }, [stack.length, nav]);
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', onBack);
    return () => sub.remove();
  }, [onBack]);

  if (!fontsLoaded || !store.ready) {
    return <View style={st.loading}><ActivityIndicator color={C.mint} /></View>;
  }

  const route = stack[stack.length - 1];
  const rootTab = stack[0].name;
  return (
    <SafeAreaProvider>
      <StoreContext.Provider value={store}>
        <SafeAreaView style={st.app} edges={['top', 'bottom']}>
          <StatusBar style="light" />
          <View style={st.body}>
            {route.name === 'home' && <Home nav={nav} />}
            {route.name === 'explore' && <Explore key={route.track ?? 'all'} nav={nav} track={route.track} />}
            {route.name === 'notes' && <NotesTab nav={nav} />}
            {route.name === 'topic' && <TopicScreen key={route.id} nav={nav} id={route.id} />}
            {route.name === 'lesson' && <LessonScreen key={route.id} nav={nav} id={route.id} />}
          </View>
          <View style={st.tabs} accessibilityRole="tablist">
            {TABS.map((t) => {
              const active = rootTab === t.route.name;
              return (
                <Pressable key={t.label} onPress={() => nav.tab(t.route)} accessibilityRole="tab"
                  accessibilityState={{ selected: active }} style={st.tab}>
                  <View style={[st.tabMark, active && st.tabMarkOn]} />
                  <Text style={[st.tabText, active && st.tabTextOn]}>{t.label}</Text>
                </Pressable>
              );
            })}
          </View>
        </SafeAreaView>
      </StoreContext.Provider>
    </SafeAreaProvider>
  );
}

const st = StyleSheet.create({
  loading: { flex: 1, backgroundColor: C.ground, alignItems: 'center', justifyContent: 'center' },
  app: { flex: 1, backgroundColor: C.ground },
  body: { flex: 1 },
  tabs: { flexDirection: 'row', borderTopWidth: 1, borderTopColor: C.edge, backgroundColor: '#121212' },
  tab: { flex: 1, alignItems: 'center', justifyContent: 'center', minHeight: 56, gap: SP.xs },
  tabMark: { width: 24, height: 3, borderRadius: 2, backgroundColor: 'transparent' },
  tabMarkOn: { backgroundColor: C.mint },
  tabText: { fontFamily: F.bodySemi, fontSize: 13, color: C.muted },
  tabTextOn: { color: C.text },
});

import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View } from 'react-native';
import GameScreen from './src/GameScreen';

export default function App() {
  return (
    <View style={styles.container}>
      <StatusBar style="light" hidden />
      <GameScreen />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0F172A' },
});

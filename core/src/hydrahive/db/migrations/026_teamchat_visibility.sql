-- Etappe 5c: Räume privat (invite-only) oder offen (für alle sichtbar/beitretbar).
-- Bestehende Räume bleiben privat (Default), kein Verhaltenswechsel für Altdaten.
ALTER TABLE teamchat_rooms ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private';

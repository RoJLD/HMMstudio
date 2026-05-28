#!/bin/sh
# Re-sync the Academy slice from the studio frontend (source of truth).
# Run from the repo root: sh academy/scripts/sync-from-studio.sh
#
# After running, manually re-apply the bridge patch on
# academy/src/pages/LessonPage.tsx (see docs/plans/2026-05-28-academy-standalone.md
# Task 4): drop useNavigate/topologyStore/lib/yaml/handleTryInEditor and use
# <TryInStudioLink yaml={lesson.presetTopologyYaml} /> instead.
set -e
SRC=src/hmm_studio/frontend/src
DST=academy/src
cp "$SRC"/components/academy/*.ts "$SRC"/components/academy/*.tsx "$DST/components/academy/"
cp "$SRC"/lessons/*.ts "$SRC"/lessons/*.tsx "$DST/lessons/"
cp "$SRC/store/academyStore.ts" "$DST/store/academyStore.ts"
cp "$SRC/components/ThemeToggle.tsx" "$DST/components/ThemeToggle.tsx"
cp "$SRC/hooks/useTheme.ts" "$DST/hooks/useTheme.ts"
cp "$SRC/pages/AcademyPage.tsx" "$DST/pages/AcademyPage.tsx"
cp "$SRC/index.css" "$DST/index.css"
echo "Synced. Now re-apply the bridge patch on $DST/pages/LessonPage.tsx (see Task 4)."

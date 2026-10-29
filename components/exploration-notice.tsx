import * as React from "react";

export function ExplorationNotice({ active }: { active: boolean }) {
  return active ? <p role="status">DEVELOPMENT EXPLORATION · estimated usage recorded; warning threshold is not a spending cap</p> : null;
}

export function explorationStage(discovery: boolean) {
  return discovery ? "Exploring areas, finding more places, then checking routes" : "Checking routes and generating options";
}

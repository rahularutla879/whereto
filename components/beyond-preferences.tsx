import * as React from 'react';
import {beyondPage,beyondNotice} from '@/lib/itinerary-pages';
import type {PlannerResult} from '@/lib/planner';
export function BeyondPreferences({result}:{result:PlannerResult}){
 return result.plans.length>0&&beyondPage(result)?<div className="plan-warning" role="note"><h3>Explore beyond your preferences</h3><p>{beyondNotice(result)}</p></div>:null;
}

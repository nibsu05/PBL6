"""Freeze the extended data contract and preserve existing research artifacts."""
from pathlib import Path
import sys,json,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pandas as pd
from src.station_archive_update import BASE,OUT,PUBLIC,OLD,LAST,sha,write_json


def main():
    for p in (BASE,OUT,PUBLIC):p.mkdir(parents=True,exist_ok=True)
    preserved={}
    for folder in ('gfs_station_daily_v2_2026_11_10','gfs_daily_slides_2026_11_11','gfs_station_57_2026_11_10','gfs_station_slides_2026_11_10'):
        for p in (ROOT/'reports'/folder).rglob('*'):
            if p.is_file():preserved[p.relative_to(ROOT).as_posix()]=sha(p)
    for item in json.loads((ROOT/'data/operational/workspace_cleanup_2026_11_09/user_files.json').read_text(encoding='utf8')):
        preserved[item['path']]=item['sha256'];assert sha(ROOT/item['path'])==item['sha256']
    path=BASE/'preserved_hashes.json'
    if path.exists():assert json.loads(path.read_text(encoding='utf8'))==preserved
    else:write_json(path,preserved)
    contract=dict(version='station_update_2026_11_16',authorized_date='2026-11-16',
        purpose='extend source archive and a separate GFS daily dataset through the last complete source day; no model fitting/evaluation',
        first_marked_day='2021-01-01',last_marked_day=LAST,station_inventory=86,
        canonical_ids='preserve ST identifiers from the 2026-11-09 registry; verify current aliases/coordinates',
        namespaces=['legacy','modern'],old_data='legacy 2021--2024 reused unchanged; modern historical probes had no numbers',
        new_collection='both namespaces 2025-01-01 through 2026-11-15, including 2026-01-01; reuse verified 2026 cache',
        time_contract='source 10:00 is 09:00--10:00 Vietnam UTC+7, user confirmed; source day ends 19:00',
        qc='missing remains NaN; no imputation of labels; preserve raw; sum mismatch tolerance 1e-6 in float64',
        channel_policy='retain both; conflicting numeric channel pairs excluded from combined rain and sample readiness; never sum channels',
        hourly_combined_policy='legacy preferred when valid; modern only fills legacy absence or agrees, with explicit source/transition status',
        short_range_policy='separate namespace samples; entire rain history and target use the same namespace, no mixed history/label',
        continuity='exact current coordinates do not confirm measurement continuity; modern channel marked continuity_unverified',
        gfs=dict(init_utc=0,issue_utc=12,rain_leads=[12,36,60,84],met_leads=[24,48,72],
                 raw_variables=['T850','RH850','U850','V850','PWAT'],grid_degrees=.25,interpolation='four-node strict bilinear',
                 first_issue_day='2021-01-08',last_issue_day='2026-11-12',delay_assumed_hours=8,
                 instantaneous_met='window-midpoint states, not day means'),
        history=dict(days=7,recent_hours=[1,6,24],gauge_delay_hours=[1,3,6]),
        terrain='same Mapzen DEM transform as daily-v2, 9-point neighborhood and 10km finite-difference slopes',
        evaluation_roles={'2021-2022':'train_old_contract','2023':'calibration_old_contract','2024':'development_old_contract',
                          '2025':'reserved_unscored','2026':'recent_external_unscored'},
        model_protocol='unchanged; collecting/building 2025 is now authorized, but no scoring or retuning authorized by this data request',
        previous_final_holdout='not claimed untouched at observation level after this release; still no model score or fitting on 2025',
        modern_training_ready=False,feature_groups='N0--N5 of GFS daily-v2; this release does not extend the old 44-channel ERA5 dataset',
        publication='only code, documentation and aggregate coverage/QC; no observations, station coordinates or credentials in public Git')
    path=PUBLIC/'data_contract.json'
    if path.exists():assert json.loads(path.read_text(encoding='utf8'))==contract
    else:write_json(path,contract)
    write_json(BASE/'contract_lock.json',dict(sha256=sha(path)))
    terrain_folder=BASE/'terrain';terrain_folder.mkdir(exist_ok=True)
    for p in (ROOT/'data/operational/gfs_station_pilot_2026_11_10/terrain').glob('*.hgt.gz'):
        target=terrain_folder/p.name
        if not target.exists():shutil.copy2(p,target)
        else:assert sha(target)==sha(p)
    from scripts import prepare_gfs_station_pilot as terrain_module
    terrain_module.BASE=BASE
    registry=pd.read_csv(BASE/'station_registry_private.csv',dtype={'legacy_id':str,'modern_id':str})
    from src.vrain_export_audit import inventory_from_groups
    for channel in ('legacy','modern'):
        current=inventory_from_groups(json.loads((BASE/f'groups_{channel}_current_private.json').read_text(encoding='utf8')))
        current={item['station_id']:item for item in current}
        selected=registry.loc[registry[channel+'_id'].notna()]
        assert set(selected[channel+'_id'])==set(current),'Inventory changed; define an explicit ID extension before proceeding'
        for row in selected.itertuples():
            item=current[getattr(row,channel+'_id')]
            assert abs(row.latitude-item['latitude'])<1e-10 and abs(row.longitude-item['longitude'])<1e-10,'Coordinate changed'
    terrain=terrain_module.terrain(registry)
    old_terrain=pd.read_csv(ROOT/'data/operational/gfs_station_pilot_2026_11_10/station_terrain_private.csv')
    compare=old_terrain.merge(terrain,on='canonical_id',suffixes=('_old','_new'))
    for col in ('dem_elev_m','dem_mean_5km_m','dem_std_5km_m','dem_slope_east','dem_slope_north'):
        assert __import__('numpy').allclose(compare[col+'_old'],compare[col+'_new'],rtol=0,atol=1e-10)
    terrain.to_csv(BASE/'station_terrain_private.csv',index=False)
    print(json.dumps(dict(contract_frozen=True,preserved_files=len(preserved),terrain_stations=len(terrain),training_run=False)))


if __name__=='__main__':main()

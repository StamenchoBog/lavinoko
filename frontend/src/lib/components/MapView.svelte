<script lang="ts">
  // The map. MapLibre is loaded only after the panel is on screen, so the forecast shows first.
  import { onMount } from 'svelte';
  import { base } from '#lib/paths.ts';
  import type { FilterSpecification, Map as MlMap, Marker, StyleSpecification } from 'maplibre-gl';
  import { mapHandle, type GridLine, type MapPicture, type SnapshotRequest } from '#lib/mapHandle.ts';
  import { data, currentPlace, selectPlace, t, ui } from '#lib/state.svelte.ts';

  let { dataBase }: { dataBase: string } = $props();

  let container: HTMLDivElement;
  let bearing = $state(0);
  let map: MlMap | undefined = $state();
  let MarkerClass: typeof Marker;
  const placeMarkers: Record<string, { marker: Marker; el: HTMLElement }> = {};
  let pointMarkers: { marker: Marker; el: HTMLElement; id: string }[] = [];
  let firstRun = true;
  let sharedView = false; // the address bar already had a map position when the page opened
  let reportMarkers: Marker[] = [];
  let draftMarker: Marker | null = null;

  const narrow = () => matchMedia('(max-width: 560px)').matches;
  // The panel covers the left side (desktop) or the lower half (phone); keep the map's focus clear of it.
  const panelPadding = () =>
    narrow()
      ? { top: 20, left: 10, right: 10, bottom: Math.round(innerHeight * 0.5) }
      : { top: 20, left: 400, right: 20, bottom: 20 };

  onMount(() => {
    let cancelled = false;
    let created: MlMap | undefined;
    (async () => {
      const [{ default: maplibregl }, { Protocol }] = await Promise.all([
        import('maplibre-gl'),
        import('pmtiles'),
        import('maplibre-gl/dist/maplibre-gl.css')
      ]);
      if (cancelled) return;
      maplibregl.addProtocol('pmtiles', new Protocol().tile);
      MarkerClass = maplibregl.Marker;

      const meta = data.meta!;
      const style = await baseMapStyle();
      if (cancelled) return;
      const [w, s, e, n] = meta.bounds;
      sharedView = /^#[\d.]+\//.test(location.hash);
      created = new maplibregl.Map({
        container,
        bounds: [w + 0.2, s + 0.1, e - 0.2, n - 0.1],
        fitBoundsOptions: { padding: panelPadding() },
        // A tall phone screen (half of it under the panel) needs more room north and south to show the whole country.
        maxBounds: narrow() ? [[w - 0.6, s - 2], [e + 0.6, n + 1]] : [[w - 0.6, s - 0.4], [e + 0.6, n + 0.4]],
        minZoom: narrow() ? 6.5 : 7, // a phone needs to zoom out further to fit the whole country
        maxZoom: 16,
        hash: true, // map position in the address bar, so a view can be shared
        style,
        attributionControl: { compact: true }
      });
      created.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
      created.addControl(
        new maplibregl.GeolocateControl({ positionOptions: { enableHighAccuracy: true }, trackUserLocation: true, showAccuracyCircle: true }),
        'top-right'
      );
      created.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right');
      created.setPadding(panelPadding());
      created.on('rotate', () => (bearing = created!.getBearing()));
      created.on('click', (e) => {
        // While the report form is open, a tap on the map sets the report's point.
        if (ui.reportForm) ui.draftPoint = { lat: e.lngLat.lat, lon: e.lngLat.lng };
        else ui.inspect = { lat: e.lngLat.lat, lon: e.lngLat.lng };
      });
      created.on('load', () => {
        map = created;
        simplifyBaseMap(created!);
        addLayers();
        addPlaceMarkers();
        mapHandle.snapshot = snapshot;
      });
    })();
    return () => {
      cancelled = true;
      created?.remove();
    };
  });

  const MIN_PRINT_WIDTH_M = 8000;

  /**
   * Our own base map (backend/basemap/build_basemap.py) when it has been built; otherwise the public
   * OpenFreeMap style, which uses the same data schema, so all our layers work with either.
   */
  async function baseMapStyle(): Promise<string | StyleSpecification> {
    try {
      const r = await fetch(`${base}/data/basemap/style.json`);
      if (r.ok) {
        const site = new URL(`${base}/`, location.href).href.replace(/\/$/, '');
        return JSON.parse((await r.text()).replaceAll('{base}', site));
      }
    } catch {
      /* not built: use the public style */
    }
    return 'https://tiles.openfreemap.org/styles/liberty';
  }

  /** A round grid step giving a handful of lines across `span` degrees. */
  function gridStep(span: number): number {
    const steps = [0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1];
    return steps.find((st) => span / st <= 6) ?? 1;
  }

  /**
   * Print picture of the slope map, framed on what the user is looking at (the part not covered by
   * the panel). It is rendered off-screen at a fixed size, so the print is sharp on any device, and
   * the grid lines and points are measured while the map is at that exact view.
   */
  async function snapshot(req: SnapshotRequest): Promise<MapPicture | null> {
    const m = map;
    if (!m) return null;
    const pad = m.getPadding();
    const before = { center: m.getCenter(), zoom: m.getZoom(), padding: pad };
    const canvas = m.getCanvas();
    const visibleWidth = Math.max(200, canvas.clientWidth - (pad.left ?? 0) - (pad.right ?? 0));
    const visibleHeight = Math.max(200, canvas.clientHeight - (pad.top ?? 0) - (pad.bottom ?? 0));
    // Centre of the part of the map the user can see (beside / above the panel).
    let center: { lng: number; lat: number } = m.unproject([(pad.left ?? 0) + visibleWidth / 2, (pad.top ?? 0) + visibleHeight / 2]);
    // Same ground width as on screen, but at least MIN_PRINT_WIDTH_M: a tour needs its surroundings,
    // and the 10 m terrain cells would print as visible blocks when zoomed in further.
    const cosLat = Math.cos((center.lat * Math.PI) / 180);
    const maxZoom = Math.log2((40075016.686 * cosLat * req.width) / (512 * MIN_PRINT_WIDTH_M));
    let zoom = Math.min(maxZoom, before.zoom + Math.log2(req.width / visibleWidth));

    // The printed map must show every forecast point (the emergency box lists their coordinates):
    // if one falls outside, frame the view centre and all points together.
    const mercY = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
    const lonsAll = [center.lng, ...req.points.map((p) => p[0])];
    const latsAll = [center.lat, ...req.points.map((p) => p[1])];
    const fits = (z: number, c: { lng: number; lat: number }) => {
      const world = 512 * 2 ** z;
      return req.points.every(([lon, lat]) => {
        const x = ((lon - c.lng) / 360) * world / req.width + 0.5;
        const y = ((mercY(c.lat) - mercY(lat)) / (2 * Math.PI)) * world / req.height + 0.5;
        return x > 0.06 && x < 0.94 && y > 0.08 && y < 0.92;
      });
    };
    if (!fits(zoom, center)) {
      const w = Math.min(...lonsAll), e = Math.max(...lonsAll), s = Math.min(...latsAll), n = Math.max(...latsAll);
      center = { lng: (w + e) / 2, lat: (s + n) / 2 };
      while (zoom > 8 && !fits(zoom, center)) zoom -= 0.1;
    }
    const markers = [...container.querySelectorAll<HTMLElement>('.maplibregl-marker')];
    const layerVis = (['slope', 'aspect'] as const).map((l) => [l, m.getLayoutProperty(`${l}-country`, 'visibility')] as const);
    const style = container.getAttribute('style') ?? '';

    try {
      markers.forEach((el) => (el.style.visibility = 'hidden'));
      for (const scope of ['country', 'detail']) {
        m.setLayoutProperty(`slope-${scope}`, 'visibility', 'visible');
        m.setLayoutProperty(`aspect-${scope}`, 'visibility', 'none');
      }
      container.style.cssText = `position:fixed;left:0;top:0;width:${req.width}px;height:${req.height}px;`;
      m.resize();
      m.setPadding({ top: 0, left: 0, right: 0, bottom: 0 });
      m.jumpTo({ center, zoom });
      await new Promise<void>((r) => m.once('idle', () => r()));
      // The drawing buffer is only readable during a render, so capture inside the render event.
      const url = await new Promise<string>((resolve) => {
        m.once('render', () => resolve(m.getCanvas().toDataURL('image/jpeg', 0.9)));
        m.triggerRepaint();
      });

      // Positions from the Web Mercator formulas for this exact centre and zoom (512-px tiles),
      // independent of the map's internal state during the off-screen resize.
      const world = 512 * 2 ** zoom;
      const wx = (lon: number) => ((lon + 180) / 360) * world;
      const wy = (lat: number) => ((1 - Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360)) / Math.PI) / 2) * world;
      const fromWy = (y: number) => (Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / world))) * 180) / Math.PI;
      const fx = (lon: number) => (wx(lon) - wx(center.lng)) / req.width + 0.5;
      const fy = (lat: number) => (wy(lat) - wy(center.lat)) / req.height + 0.5;
      const west = center.lng - (req.width / 2 / world) * 360;
      const east = center.lng + (req.width / 2 / world) * 360;
      const north = fromWy(wy(center.lat) - req.height / 2);
      const south = fromWy(wy(center.lat) + req.height / 2);

      const step = gridStep(east - west);
      const lons: GridLine[] = [];
      const lats: GridLine[] = [];
      for (let v = Math.ceil(west / step) * step; v < east; v += step) lons.push({ value: +v.toFixed(4), at: fx(v) });
      for (let v = Math.ceil(south / step) * step; v < north; v += step) lats.push({ value: +v.toFixed(4), at: fy(v) });
      const points = req.points.map(([lon, lat]) => {
        const x = fx(lon), y = fy(lat);
        return x >= 0 && x <= 1 && y >= 0 && y <= 1 ? { x, y } : null;
      });
      const widthMeters = ((40075016.686 * cosLat) / world) * req.width;
      return { url, width: req.width, height: req.height, widthMeters, step, lons, lats, points };
    } finally {
      container.setAttribute('style', style);
      m.resize();
      for (const [l, v] of layerVis) for (const scope of ['country', 'detail']) m.setLayoutProperty(`${l}-${scope}`, 'visibility', v ?? 'visible');
      markers.forEach((el) => (el.style.visibility = ''));
      m.setPadding(before.padding);
      m.jumpTo({ center: before.center, zoom: before.zoom });
    }
  }

  function addLayers() {
    const m = map!;
    const meta = data.meta!;
    // Overlays go below the first label layer so place names stay readable.
    const firstLabel = m.getStyle().layers.find((l) => l.type === 'symbol')?.id;
    const abs = new URL(dataBase, location.href).href;
    // Country layers (zoom 8-13, enlarged beyond) with detail layers (zoom 14-15) on top where they exist.
    for (const name of ['relief', 'aspect', 'slope', 'contours'] as const) {
      for (const scope of ['country', 'detail'] as const) {
        const id = `${name}-${scope}`;
        m.addSource(id, { type: 'raster', url: `pmtiles://${abs}terrain/${meta.layers[name][scope]}`, tileSize: 256 });
        const countryMin = name === 'contours' ? 11.5 : 7.5;
        m.addLayer(
          {
            id, type: 'raster', source: id,
            minzoom: scope === 'detail' ? meta.detail_zooms[0] : countryMin,
            paint: { 'raster-opacity': name === 'slope' || name === 'aspect' ? 0.8 : 1, 'raster-fade-duration': 0 }
          },
          firstLabel
        );
      }
    }
    addOutdoorLayers(m);
    addOutsideMask(m);
  }

  // Base-map detail that doesn't help in the mountains: hidden, so less is drawn and the terrain reads clearly.
  const HIDDEN_BASE_LAYERS = [
    /^building/, /^poi_/, /^aeroway_/, /^landuse_(pitch|track|cemetery|hospital|school)$/, /^road_one_way/,
    /_hatching$/, /^highway-name-(path|minor)$/, /^highway-shield-us/, /^label_country/, /^label_state$/, /^label_other$/,
    // City detail: minor streets, link roads and residential areas.
    /^(road|tunnel|bridge)_(minor|street|link)(_casing)?$/, /^landuse_residential$/
  ];

  function simplifyBaseMap(m: MlMap) {
    for (const l of m.getStyle().layers) {
      if (HIDDEN_BASE_LAYERS.some((re) => re.test(l.id))) m.removeLayer(l.id);
    }
    // Village names only when zoomed in.
    if (m.getLayer('label_village')) m.setLayerZoomRange('label_village', 11, 24);
  }

  /** Fade everything outside North Macedonia (border from OpenStreetMap), on top of all map layers. */
  async function addOutsideMask(m: MlMap) {
    const border = await fetch(`${base}/border.geojson`).then((r) => r.json()).catch(() => null);
    if (!border || !map) return;
    const world = [[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]];
    m.addSource('outside', {
      type: 'geojson',
      data: { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [world, ...border.geometry.coordinates] } }
    });
    m.addLayer({ id: 'outside-mask', type: 'fill', source: 'outside', // Fades out when zoomed in: the ranges straddle the border and their terrain matters on both sides.
    paint: { 'fill-color': '#eef1f4', 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 9, 0.72, 11.5, 0] } });
    m.addSource('border', { type: 'geojson', data: border });
    m.addLayer({ id: 'border-line', type: 'line', source: 'border', paint: { 'line-color': '#17283a', 'line-opacity': 0.55, 'line-width': 1.4 } });
  }

  /**
   * What matters in avalanche terrain, drawn from the base map's OpenStreetMap data: trails and
   * tracks, ski lifts, mountain huts, and peaks with their heights.
   */
  function addOutdoorLayers(m: MlMap) {
    const src = 'openmaptiles';
    const font = ['Noto Sans Bold'];
    const halo = { 'text-halo-color': '#ffffff', 'text-halo-width': 1.6 };
    const firstLabel = m.getStyle().layers.find((l) => l.type === 'symbol')?.id;
    m.addLayer({
      id: 'outdoor-trails', type: 'line', source: src, 'source-layer': 'transportation', minzoom: 11,
      filter: ['match', ['get', 'class'], ['path', 'track'], true, false],
      paint: {
        'line-color': '#7a3b12',
        'line-width': ['interpolate', ['linear'], ['zoom'], 11, 0.8, 15, 2],
        'line-dasharray': [2.5, 1.5]
      }
    }, firstLabel);
    m.addLayer({
      id: 'outdoor-lifts', type: 'line', source: src, 'source-layer': 'transportation', minzoom: 11,
      filter: ['==', ['get', 'class'], 'aerialway'],
      paint: { 'line-color': '#17283a', 'line-width': ['interpolate', ['linear'], ['zoom'], 11, 1, 15, 2.2] }
    }, firstLabel);
    m.addLayer({
      id: 'outdoor-huts', type: 'symbol', source: src, 'source-layer': 'poi', minzoom: 12,
      filter: ['match', ['get', 'subclass'], ['alpine_hut', 'wilderness_hut', 'shelter'], true, false],
      layout: { 'text-field': ['concat', '⌂ ', ['coalesce', ['get', 'name'], '']], 'text-font': font, 'text-size': 11, 'text-anchor': 'top' },
      paint: { 'text-color': '#7a3b12', ...halo }
    });
    m.addLayer({
      id: 'outdoor-peaks', type: 'symbol', source: src, 'source-layer': 'mountain_peak', minzoom: 10,
      filter: ['has', 'ele'],
      layout: {
        'text-field': ['concat', '▲ ', ['coalesce', ['get', 'name'], ''], '\n', ['to-string', ['get', 'ele']], ' m'],
        'text-font': font, 'text-size': ['interpolate', ['linear'], ['zoom'], 10, 10, 14, 12], 'text-anchor': 'top',
        'symbol-sort-key': ['-', 0, ['get', 'ele']]
      },
      paint: { 'text-color': '#17283a', ...halo }
    });
  }

  /** Invisible padding left of a place symbol: with it the tap target is 48 px, and the symbol stays on the place. */
  const MARKER_PAD = 18;

  function addPlaceMarkers() {
    for (const p of data.weather?.places ?? []) {
      const el = document.createElement('button');
      el.className = `place-marker ${p.kind}`;
      el.innerHTML = '<i></i><span></span>';
      el.addEventListener('click', (ev) => {
        ev.stopPropagation();
        // While writing a report, a marker tap sets the report's point instead of navigating.
        if (ui.reportForm) ui.draftPoint = { lat: p.center[1], lon: p.center[0] };
        else selectPlace(p.id);
      });
      placeMarkers[p.id] = { el, marker: new MarkerClass({ element: el, anchor: 'left', offset: [-MARKER_PAD - 6, 0] }).setLngLat(p.center).addTo(map!) };
    }
    const m = map!;
    const labels = () => container.classList.toggle('far', m.getZoom() < (narrow() ? 9.5 : 8.6));
    m.on('zoom', labels);
    labels();
  }

  $effect(() => {
    if (!map) return;
    for (const p of data.weather?.places ?? []) {
      const m = placeMarkers[p.id];
      if (!m) continue;
      const snow = p.headline.snow_next72_cm;
      m.el.querySelector('span')!.textContent = snow >= 1 ? `${p.name[ui.lang]} ${Math.round(snow)} cm` : p.name[ui.lang];
      const lvl = p.level === 'serious' ? t().level_serious : p.level === 'attention' ? t().level_attention : '';
      m.el.title = p.name[ui.lang];
      m.el.setAttribute('aria-label', [p.name[ui.lang], lvl, snow >= 1 ? `${Math.round(snow)} cm` : ''].filter(Boolean).join(', '));
      m.el.classList.toggle('snow', snow >= 1);
      m.el.classList.toggle('attention', p.level === 'attention');
      m.el.classList.toggle('serious', p.level === 'serious');
      m.el.style.display = p.id === ui.place ? 'none' : '';
    }
  });

  /** Hide peak labels right under a forecast-point pill: the pill marks that summit and shows its height. */
  function setPeakFilter(points: { lon: number; lat: number }[] | null) {
    if (!map?.getLayer('outdoor-peaks')) return;
    if (!points?.length) {
      map.setFilter('outdoor-peaks', ['has', 'ele']);
      return;
    }
    const box = (lon: number, lat: number) => {
      const dx = 0.005, dy = 0.003; // about 400 m by 330 m
      return [[[lon - dx, lat - dy], [lon + dx, lat - dy], [lon + dx, lat + dy], [lon - dx, lat + dy], [lon - dx, lat - dy]]];
    };
    const near = { type: 'MultiPolygon', coordinates: points.map((p) => box(p.lon, p.lat)) };
    map.setFilter('outdoor-peaks', ['all', ['has', 'ele'], ['!', ['within', near]]] as FilterSpecification);
  }

  $effect(() => {
    const place = currentPlace();
    if (!map) return;
    for (const pm of pointMarkers) pm.marker.remove();
    pointMarkers = [];
    const first = firstRun;
    firstRun = false;
    if (!place) {
      // On first load keep a shared position from the address bar; otherwise fit the country again,
      // because the map's first fit ran before its container had its final size.
      setPeakFilter(null);
      if (!first || !sharedView) {
        const [w, s, e, n] = data.meta!.bounds;
        map.fitBounds([w + 0.2, s + 0.1, e - 0.2, n - 0.1], { duration: first ? 0 : 600, padding: 0 });
      }
      return;
    }
    for (const p of place.points) {
      const el = document.createElement('button');
      el.className = 'wx-marker';
      // The pill is drawn by the span; the button around it is the 48 px tap target.
      el.append(Object.assign(document.createElement('span'), { textContent: `${p.elevation} m` }));
      el.setAttribute('aria-label', `${p.name[ui.lang]}, ${p.elevation} m`);
      el.addEventListener('click', (ev) => {
        ev.stopPropagation();
        if (ui.reportForm) {
          ui.draftPoint = { lat: p.lat, lon: p.lon };
          return;
        }
        ui.point = p.id;
        ui.tab = 'weather';
      });
      // Points that share a position (summit and treeline) are fanned out so both stay clickable.
      const twin = place.points.filter((q) => q.lon === p.lon && q.lat === p.lat);
      const offset: [number, number] = twin.length > 1 ? [0, (twin.indexOf(p) - (twin.length - 1) / 2) * 26] : [0, 0];
      pointMarkers.push({ el, id: p.id, marker: new MarkerClass({ element: el, offset }).setLngLat([p.lon, p.lat]).addTo(map) });
    }
    setPeakFilter(place.points);
    // Zoom 13 around the place, but zoom out if needed so every forecast point stays on screen (narrow phones).
    const lons = [place.center[0], ...place.points.map((p) => p.lon)];
    const lats = [place.center[1], ...place.points.map((p) => p.lat)];
    const cam = map.cameraForBounds([Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)], { padding: { top: 50, bottom: 50, left: 60, right: 90 }, maxZoom: 13 } /* right: clear of the map buttons */);
    map.flyTo({ center: cam?.center ?? place.center, zoom: Math.max(12, cam?.zoom ?? 13), /* the base map has ski lifts from zoom 12 */ duration: 900, essential: true });
  });

  $effect(() => {
    const selected = ui.point;
    for (const pm of pointMarkers) pm.el.classList.toggle('on', pm.id === selected);
  });

  $effect(() => {
    const reports = data.reports;
    if (!map) return;
    for (const m of reportMarkers) m.remove();
    reportMarkers = reports.map((r) => {
      const el = document.createElement('button');
      el.className = `report-marker${r.kinds.includes('avalanche') ? ' avalanche' : ''}`;
      el.title = r.kinds.join(', ');
      el.addEventListener('click', (ev) => {
        ev.stopPropagation();
        if (r.place_id) ui.place = r.place_id;
        ui.tab = 'reports';
      });
      return new MarkerClass({ element: el }).setLngLat([r.lon, r.lat]).addTo(map!);
    });
  });

  // The tapped point (inspector).
  let inspectMarker: Marker | null = null;
  $effect(() => {
    const p = ui.inspect;
    if (!map) return;
    inspectMarker?.remove();
    inspectMarker = p ? new MarkerClass({ color: '#b3261e' }).setLngLat([p.lon, p.lat]).addTo(map) : null;
    // On phones the point card covers the lower half: keep the pin in view above it.
    if (p && narrow()) map.easeTo({ center: [p.lon, p.lat], padding: { top: 20, left: 10, right: 10, bottom: Math.round(innerHeight * 0.55) }, duration: 400 });
    else if (!p) {
      // setPadding() jumps the camera and would cancel a running flyTo (e.g. opening a ?place= link), so only reset when needed.
      const want = panelPadding();
      const have = map.getPadding();
      if ((['top', 'right', 'bottom', 'left'] as const).some((k) => want[k] !== have[k])) map.setPadding(want);
    }
  });

  $effect(() => {
    const pt = ui.draftPoint;
    const open = ui.reportForm;
    if (!map) return;
    if (!open || !pt) {
      draftMarker?.remove();
      draftMarker = null;
      return;
    }
    if (!draftMarker) {
      draftMarker = new MarkerClass({ color: '#2468a8', draggable: true }).setLngLat([pt.lon, pt.lat]).addTo(map);
      draftMarker.on('dragend', () => {
        const ll = draftMarker!.getLngLat();
        ui.draftPoint = { lat: ll.lat, lon: ll.lng };
      });
    } else {
      draftMarker.setLngLat([pt.lon, pt.lat]);
    }
  });
  $effect(() => {
    if (map) map.getCanvas().style.cursor = ui.reportForm ? 'crosshair' : '';
  });

  $effect(() => {
    if (!map) return;
    for (const scope of ['country', 'detail']) {
      map.setLayoutProperty(`slope-${scope}`, 'visibility', ui.layer === 'slope' ? 'visible' : 'none');
      map.setLayoutProperty(`aspect-${scope}`, 'visibility', ui.layer === 'aspect' ? 'visible' : 'none');
      map.setLayoutProperty(`relief-${scope}`, 'visibility', ui.relief ? 'visible' : 'none');
      map.setLayoutProperty(`contours-${scope}`, 'visibility', ui.contours ? 'visible' : 'none');
    }
  });
</script>

<div class="map" bind:this={container} role="region" aria-label={t().map_label}></div>
{#if map}
  <button class="rose" title="N" aria-label="North up" onclick={() => map?.easeTo({ bearing: 0, pitch: 0 })}>
    <svg viewBox="-20 -20 40 40" aria-hidden="true" style="transform: rotate({-bearing}deg)">
      <circle r="18.5" class="ring" />
      <path d="M0 -9 L3.2 0 L0 -1.5 L-3.2 0 Z" class="n" />
      <path d="M0 9 L3.2 0 L0 1.5 L-3.2 0 Z" class="s" />
      <text y="-13.6" class="lbl strong">N</text>
      <text x="13.6" y="0.4" class="lbl">E</text>
      <text y="14" class="lbl">S</text>
      <text x="-13.6" y="0.4" class="lbl">W</text>
    </svg>
  </button>
{/if}

<style>
  .map { position: absolute; inset: 0; }
  .rose {
    position: absolute; top: 122px; right: 10px; width: 46px; height: 46px; padding: 0; border: 0; border-radius: 50%;
    background: #fff; box-shadow: 0 0 0 2px #0000001a; cursor: pointer;
  }
  .rose svg { width: 100%; height: 100%; transition: transform 0.2s; }
  .ring { fill: #fff; stroke: #dce2e8; stroke-width: 1; }
  .n { fill: var(--serious); }
  .s { fill: #9aa6b2; }
  .lbl { font: 700 7.5px system-ui, sans-serif; fill: var(--muted); text-anchor: middle; dominant-baseline: middle; }
  .lbl.strong { font-weight: 900; fill: var(--serious); }
  @media (prefers-reduced-motion: reduce) { .rose svg { transition: none; } }
  @media print { .rose { display: none; } }
  :global(.wx-marker) {
    display: grid; place-items: center; min-height: 48px; padding: 0 4px; border: 0; background: none; cursor: pointer;
  }
  :global(.wx-marker span) {
    border-radius: 12px; padding: 2px 8px; font: 700 12px system-ui, sans-serif;
    white-space: nowrap; box-shadow: 0 1px 4px #0003; background: #fff; border: 2px solid var(--ink); color: var(--ink);
  }
  :global(.wx-marker.on span) { background: var(--glacier); border-color: var(--glacier); color: #fff; }

  /* Places: a symbol (circle = ski area, triangle = summit) with the name beside it. */
  :global(.place-marker) {
    display: flex; align-items: center; gap: 4px; border: 0; background: none; cursor: pointer;
    min-height: 48px; padding: 0 18px; /* 18 px = MARKER_PAD: a 48 px target around a 12 px symbol */
    font: 700 12px system-ui, sans-serif; color: var(--ink); white-space: nowrap;
  }
  :global(.place-marker i) {
    width: 12px; height: 12px; border-radius: 50%; background: var(--ink); border: 2px solid #fff; box-shadow: 0 0 0 1px #17283a55;
  }
  :global(.place-marker.touring i) {
    border-radius: 0; border: 0; box-shadow: none; width: 14px; height: 12px;
    clip-path: polygon(50% 0, 100% 100%, 0 100%); background: var(--ink);
  }
  :global(.place-marker span) {
    background: #ffffffe6; border-radius: 4px; padding: 1px 5px; box-shadow: 0 1px 3px #0002;
  }
  :global(.place-marker.snow i) { background: var(--glacier); }
  :global(.place-marker.snow span) { color: var(--glacier); }
  :global(.place-marker.attention i) { background: var(--signal); }
  :global(.place-marker.serious i) { background: var(--serious); }
  :global(.place-marker.attention i), :global(.place-marker.serious i) { width: 15px; height: 15px; }
  :global(.map.far .place-marker span) { display: none; }
  :global(.report-marker) {
    width: 13px; height: 13px; padding: 0; border: 2px solid #fff; background: #5b3fa0; transform: rotate(45deg);
    box-shadow: 0 0 0 1px #17283a66; cursor: pointer;
  }
  :global(.report-marker.avalanche) { background: var(--ink); width: 15px; height: 15px; }
  @media (max-width: 560px) {
    :global(.maplibregl-ctrl-bottom-right) { display: none; }
  }
  /* Touch screens (gloves): 48 px map buttons; the compass moves down below them. */
  @media (pointer: coarse) {
    /* More specific than MapLibre's own rule, which loads after this one. */
    :global(.maplibregl-ctrl.maplibregl-ctrl-group button) { width: 48px; height: 48px; }
    .rose { top: 174px; width: 48px; height: 48px; }
  }
</style>

//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1;
function t() {
	e = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
t();
//#endregion
//#region node_modules/svelte/src/constants.js
var n = {}, r = Symbol("uninitialized"), i = "http://www.w3.org/1999/xhtml", a = Array.isArray, o = Array.prototype.indexOf, s = Array.prototype.includes, c = Array.from, l = Object.keys, u = Object.defineProperty, d = Object.getOwnPropertyDescriptor, f = Object.getOwnPropertyDescriptors, p = Object.prototype, m = Array.prototype, h = Object.getPrototypeOf, g = Object.isExtensible, ee = () => {};
function te(e) {
	return e();
}
function _(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function v() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var y = 1024, b = 2048, x = 4096, ne = 8192, re = 16384, ie = 32768, ae = 1 << 25, oe = 65536, se = 1 << 19, ce = 1 << 20, le = 65536, ue = 1 << 21, de = 1 << 22, fe = 1 << 23, pe = Symbol("$state"), me = Symbol("component"), he = Symbol("legacy props"), ge = Symbol(""), _e = Symbol("attributes"), ve = Symbol("class"), ye = Symbol("style"), be = Symbol("text"), xe = Symbol("form reset"), Se = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), Ce = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function we() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Te(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Ee() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var S = !1;
function De(e) {
	S = e;
}
var C;
function w(e) {
	if (e === null) throw Te(), n;
	return C = e;
}
function Oe() {
	return w(/* @__PURE__ */ F(C));
}
function T(e) {
	if (S) {
		if (/* @__PURE__ */ F(C) !== null) throw Te(), n;
		C = e;
	}
}
function ke(e = 1) {
	if (S) {
		for (var t = e, n = C; t--;) n = /* @__PURE__ */ F(n);
		C = n;
	}
}
function Ae(e = !0) {
	for (var t = 0, n = C;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ F(n);
		e && n.remove(), n = i;
	}
}
function je(e) {
	if (!e || e.nodeType !== 8) throw Te(), n;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Me(e) {
	return e === this.v;
}
function Ne(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Pe(e) {
	return !Ne(e, this.v);
}
function Fe(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function Ie() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Le(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Re() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function ze(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Be() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Ve() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function He(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Ue() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function We() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Ge() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Ke() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var E = null;
function qe(e) {
	E = e;
}
function Je(t, n = !1, r) {
	E = {
		p: E,
		i: !1,
		c: null,
		e: null,
		s: t,
		x: null,
		r: K,
		l: e && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Ye(e) {
	var t = E, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) mn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, E = t.p, Xe(e);
}
function Xe(e = {}) {
	return u(e, me, { value: !0 }), e;
}
function Ze() {
	return !e || E !== null && E.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Qe = [];
function $e() {
	var e = Qe;
	Qe = [], _(e);
}
function D(e) {
	if (Qe.length === 0 && !Dt) {
		var t = Qe;
		queueMicrotask(() => {
			t === Qe && $e();
		});
	}
	Qe.push(e);
}
function et() {
	for (; Qe.length > 0;) $e();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var tt = ~(b | x | y);
function O(e, t) {
	e.f = e.f & tt | t;
}
function nt(e) {
	e.f & 512 || e.deps === null ? O(e, y) : O(e, x);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function rt(e) {
	if (e !== null) for (let t of e) t.f & 2 && t.f & 65536 && (t.f ^= le, rt(t.deps));
}
function it(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), rt(e.deps), O(e, y);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var at = !1;
function ot(e) {
	var t = at;
	try {
		return at = !1, [e(), at];
	} finally {
		at = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var st = !1;
function ct() {
	st || (st = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[xe]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function lt(e) {
	var t = U, n = K;
	G(null), q(null);
	try {
		return e();
	} finally {
		G(t), q(n);
	}
}
function ut(e, t, n, r = n) {
	e.addEventListener(t, () => lt(n));
	let i = e[xe];
	e[xe] = i ? () => {
		i(), r(!0);
	} : () => r(!0), ct();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function dt(e, t, n, r) {
	let i = Ze() ? ht : vt;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = K, c = ft(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				R(e, s);
			}
			pt();
		}
	}
	var d = mt();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ _t(e))).then(u).catch((e) => R(e, s)).finally(d);
	}
	l ? l.then(() => {
		c(), f(), pt();
	}) : f();
}
function ft() {
	var e = K, t = U, n = E, r = k;
	return function(i = !0) {
		q(e), G(t), qe(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function pt(e = !0) {
	q(null), G(null), qe(null), e && k?.deactivate();
}
function mt() {
	var e = K, t = e.b, n = k, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function ht(e) {
	var t = 2 | b;
	return K !== null && (K.f |= se), {
		ctx: E,
		deps: null,
		effects: null,
		equals: Me,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: r,
		wv: 0,
		parent: K,
		ac: null
	};
}
var gt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function _t(e, t, n) {
	let i = K;
	i === null && Ie();
	var a = void 0, o = Ht(r), s = !U, c = /* @__PURE__ */ new Set();
	return yn(() => {
		var t = K, n = v();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== Se && n.reject(e);
			}).finally(pt);
		} catch (e) {
			n.reject(e), pt();
		}
		var r = k;
		if (s) {
			if (t.f & 32768) var l = mt();
			if (i.b?.is_rendered()) r.async_deriveds.get(t)?.reject(gt);
			else for (let e of c.values()) e.reject(gt);
			c.add(n), r.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== gt && (r.activate(), t ? (o.f |= fe, Wt(o, t)) : (o.f & 8388608 && (o.f ^= fe), Wt(o, e)), r.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), fn(() => {
		for (let e of c) e.reject(gt);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/*#__NO_SIDE_EFFECTS__*/
function vt(e) {
	let t = /* @__PURE__ */ ht(e);
	return t.equals = Pe, t;
}
function yt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function bt(e) {
	var t, n = K, i = e.parent;
	if (!H && i !== null && e.v !== r && i.f & 24576) return we(), e.v;
	q(i);
	try {
		e.f &= ~le, yt(e), t = Gn(e);
	} finally {
		q(n);
	}
	return t;
}
function xt(e) {
	var t = bt(e);
	if (!e.equals(t) && (e.wv = Hn(), (!k?.is_fork || e.deps === null) && (k === null ? e.v = t : (k.capture(e, t, !0), Tt?.capture(e, t, !0)), e.deps === null))) {
		O(e, y);
		return;
	}
	H || (A === null ? nt(e) : (dn() || k?.is_fork) && A.set(e, t));
}
function St(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && lt(() => {
		t.ac.abort(Se), t.ac = null;
	}), t.fn !== null && (t.teardown = ee), Jn(t, 0), wn(t));
}
function Ct(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && Yn(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var wt = null, k = null, Tt = null, A = null, Et = null, Dt = !1, Ot = !1, kt = null, At = null, jt = 0, Mt = 1, Nt = class e {
	id = Mt++;
	#e = !1;
	linked = !0;
	#t = null;
	#n = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = /* @__PURE__ */ new Set();
	#a = 0;
	#o = /* @__PURE__ */ new Map();
	#s = null;
	#c = [];
	#l = [];
	#u = /* @__PURE__ */ new Set();
	#d = /* @__PURE__ */ new Set();
	#f = /* @__PURE__ */ new Map();
	#p = /* @__PURE__ */ new Set();
	is_fork = !1;
	#m = !1;
	constructor() {
		wt === null ? wt = this : (wt.#n = this, this.#t = wt), wt = this;
	}
	#h() {
		if (this.is_fork) return !0;
		for (let n of this.#o.keys()) {
			for (var e = n, t = !1; e.parent !== null;) {
				if (this.#f.has(e)) {
					t = !0;
					break;
				}
				e = e.parent;
			}
			if (!t) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#f.has(e) || this.#f.set(e, {
			d: [],
			m: []
		}), this.#p.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#f.get(e);
		if (n) {
			this.#f.delete(e);
			for (var r of n.d) O(r, b), t(r);
			for (r of n.m) O(r, x), t(r);
		}
		this.#p.add(e);
	}
	#g() {
		this.#e = !0, jt++ > 1e3 && (this.#x(), Ft());
		for (let e of this.#u) this.#d.delete(e), O(e, b), this.schedule(e);
		for (let e of this.#d) O(e, x), this.schedule(e);
		let t = this.#c;
		this.#c = [], this.apply();
		var n = kt = [], r = [], i = At = [];
		for (let e of t) try {
			this.#_(e, n, r);
		} catch (t) {
			throw zt(e), this.#h() || this.discard(), t;
		}
		if (k = null, i.length > 0) {
			var a = e.ensure();
			for (let e of i) a.schedule(e);
		}
		if (kt = null, At = null, this.#h()) {
			this.#b(r), this.#b(n);
			for (let [e, t] of this.#f) Rt(e, t);
			i.length > 0 && k.#g();
			return;
		}
		let o = this.#v();
		if (o) {
			this.#b(r), this.#b(n), o.#y(this);
			return;
		}
		this.#u.clear(), this.#d.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), Tt = this, It(r), It(n), Tt = null, this.#s?.resolve();
		var s = k;
		if (this.#a === 0 && (this.#c.length === 0 || s !== null) && this.#x(), this.#c.length > 0) {
			if (s !== null) {
				let e = s;
				e.#c.push(...this.#c.filter((t) => !e.#c.includes(t)));
			} else s = this;
		}
		s !== null && (M.clear(), s.#g());
	}
	#_(e, t, n) {
		e.f ^= y;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = !!(i & 96);
			if (!(a && i & 1024 || i & 8192 || this.#f.has(r)) && r.fn !== null) {
				a ? r.f ^= y : i & 4 ? t.push(r) : Un(r) && (i & 16 && this.#d.add(r), Yn(r));
				var o = r.first;
				if (o !== null) {
					r = o;
					continue;
				}
			}
			for (; r !== null;) {
				var s = r.next;
				if (s !== null) {
					r = s;
					break;
				}
				r = r.parent;
			}
		}
	}
	#v() {
		for (var e = this.#t; e !== null;) {
			if (!e.is_fork) {
				for (let [t, [, n]] of this.current) if (e.current.has(t) && !n) return e;
			}
			e = e.#t;
		}
		return null;
	}
	#y(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve).catch(e.reject);
		}
		e.async_deriveds.clear(), this.transfer_effects(e.#u, e.#d);
		let t = (e) => {
			var n = e.reactions;
			if (n !== null && !(e.f & 2 && !(e.f & 6144))) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#d.delete(i), O(i, b), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#x(), k = this, this.#g();
	}
	#b(e) {
		for (var t = 0; t < e.length; t += 1) it(e[t], this.#u, this.#d);
	}
	capture(e, t, n = !1) {
		e.v !== r && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), A?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		k = this;
	}
	deactivate() {
		k = null, A = null;
	}
	flush() {
		try {
			Ot = !0, k = this, this.#g();
		} finally {
			jt = 0, Et = null, kt = null, At = null, Ot = !1, k = null, A = null, M.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear();
		for (let e of this.async_deriveds.values()) e.reject(gt);
		this.#x(), this.#s?.resolve();
	}
	register_created_effect(e) {
		this.#l.push(e);
	}
	increment(e, t) {
		if (this.#a += 1, e) {
			let e = this.#o.get(t) ?? 0;
			this.#o.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#a, e) {
			let e = this.#o.get(t) ?? 0;
			e === 1 ? this.#o.delete(t) : this.#o.set(t, e - 1);
		}
		this.#m || (this.#m = !0, D(() => {
			this.#m = !1, this.linked && this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#u.add(t);
		for (let e of t) this.#d.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#r.add(e);
	}
	ondiscard(e) {
		this.#i.add(e);
	}
	settled() {
		return (this.#s ??= v()).promise;
	}
	static ensure() {
		if (k === null) {
			let t = k = new e();
			!Ot && !Dt && D(() => {
				t.#e || t.flush();
			});
		}
		return k;
	}
	apply() {
		A = null;
	}
	schedule(e) {
		if (Et = e, e.b?.is_pending && e.f & 16777228 && !(e.f & 32768)) {
			e.b.defer_effect(e);
			return;
		}
		for (var t = e; t.parent !== null;) {
			t = t.parent;
			var n = t.f;
			if (kt !== null && t === K && (U === null || !(U.f & 2))) return;
			if (n & 96) {
				if (!(n & 1024)) return;
				t.f ^= y;
			}
		}
		this.#c.push(t);
	}
	#x() {
		if (this.linked) {
			var e = this.#t, t = this.#n;
			e === null || (e.#n = t), t === null ? wt = e : t.#t = e, this.linked = !1;
		}
	}
};
function Pt(e) {
	var t = Dt;
	Dt = !0;
	try {
		var n;
		for (e && (k !== null && !k.is_fork && k.flush(), n = e());;) {
			if (et(), k === null) return n;
			k.flush();
		}
	} finally {
		Dt = t;
	}
}
function Ft() {
	try {
		Be();
	} catch (e) {
		R(e, Et);
	}
}
var j = null;
function It(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Un(r) && (j = /* @__PURE__ */ new Set(), Yn(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && Dn(r), j?.size > 0)) {
				M.clear();
				for (let e of j) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) j.has(n) && (j.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || Yn(n);
					}
				}
				j.clear();
			}
		}
		j = null;
	}
}
function Lt(e) {
	k.schedule(e);
}
function Rt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), O(e, y);
		for (var n = e.first; n !== null;) Rt(n, t), n = n.next;
	}
}
function zt(e) {
	O(e, y);
	for (var t = e.first; t !== null;) zt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Bt = /* @__PURE__ */ new Set(), M = /* @__PURE__ */ new Map(), Vt = !1;
function Ht(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Me,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Ut(e, t) {
	let n = Ht(e, t);
	return In(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function N(t, n = !1, r = !0) {
	let i = Ht(t);
	return n || (i.equals = Pe), e && r && E !== null && E.l !== null && (E.l.s ??= []).push(i), i;
}
function P(e, t, n = !1) {
	return U !== null && (!W || U.f & 131072) && Ze() && U.f & 4325394 && (J === null || !J.has(e)) && Ge(), Wt(e, n ? Jt(t) : t, At);
}
function Wt(e, t, n = null) {
	if (!e.equals(t)) {
		H ? M.set(e, t) : M.has(e) || M.set(e, e.v);
		var r = Nt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && bt(t), A === null && nt(t);
		}
		e.wv = Hn(), qt(e, b, n), Ze() && K !== null && K.f & 1024 && !(K.f & 96) && (Z === null ? Ln([e]) : Z.push(e)), !r.is_fork && Bt.size > 0 && !Vt && Gt();
	}
	return t;
}
function Gt() {
	Vt = !1;
	for (let e of Bt) {
		e.f & 1024 && O(e, x);
		let t;
		try {
			t = Un(e);
		} catch {
			t = !0;
		}
		t && Yn(e);
	}
	Bt.clear();
}
function Kt(e) {
	P(e, e.v + 1);
}
function qt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Ze(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (i || s !== K) {
			var l = (c & b) === 0;
			if (l && O(s, t), c & 131072) Bt.add(s);
			else if (c & 2) {
				var u = s;
				A?.delete(u), c & 65536 || (c & 512 && (K === null || !(K.f & 2097152)) && (s.f |= le), qt(u, x, n));
			} else if (l) {
				var d = s;
				c & 16 && j !== null && j.add(d), n === null ? Lt(d) : n.push(d);
			}
		}
	}
}
function Jt(e) {
	if (typeof e != "object" || !e || pe in e || me in e) return e;
	let t = h(e);
	if (t !== p && t !== m) return e;
	var n = /* @__PURE__ */ new Map(), i = a(e), o = /* @__PURE__ */ Ut(0), s = null, c = Bn, l = (e) => {
		if (Bn === c) return e();
		var t = U, n = Bn;
		G(null), Vn(c);
		var r = e();
		return G(t), Vn(n), r;
	};
	return i && n.set("length", /* @__PURE__ */ Ut(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && Ue();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Ut(r.value, s);
				return n.set(t, e), e;
			}) : P(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var i = n.get(t);
			if (i === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Ut(r, s));
					n.set(t, e), Kt(o);
				}
			} else P(i, r), Kt(o);
			return !0;
		},
		get(t, i, a) {
			if (i === pe) return e;
			var o = n.get(i), c = i in t;
			if (o === void 0 && (!c || d(t, i)?.writable) && (o = l(() => /* @__PURE__ */ Ut(Jt(c ? t[i] : r), s)), n.set(i, o)), o !== void 0) {
				var u = Q(o);
				return u === r ? void 0 : u;
			}
			return Reflect.get(t, i, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var i = Reflect.getOwnPropertyDescriptor(e, t);
			if (i && "value" in i) {
				var a = n.get(t);
				a && (i.value = Q(a));
			} else if (i === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== r) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return i;
		},
		has(e, t) {
			if (t === pe) return !0;
			var i = n.get(t), a = i !== void 0 && i.v !== r || Reflect.has(e, t);
			return (i !== void 0 || K !== null && (!a || d(e, t)?.writable)) && (i === void 0 && (i = l(() => /* @__PURE__ */ Ut(a ? Jt(e[t]) : r, s)), n.set(t, i)), Q(i) === r) ? !1 : a;
		},
		set(e, t, a, c) {
			var u = n.get(t), f = t in e;
			if (i && t === "length") for (var p = a; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Ut(r, s)), n.set(p + "", m)) : P(m, r);
			}
			if (u === void 0) (!f || d(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Ut(void 0, s)), P(u, Jt(a)), n.set(t, u));
			else {
				f = u.v !== r;
				var h = l(() => Jt(a));
				P(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, a), !f) {
				if (i && typeof t == "string") {
					var ee = n.get("length"), te = Number(t);
					Number.isInteger(te) && te >= ee.v && P(ee, te + 1);
				}
				Kt(o);
			}
			return !0;
		},
		ownKeys(e) {
			Q(o);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== r;
			});
			for (var [i, a] of n) a.v !== r && !(i in e) && t.push(i);
			return t;
		},
		setPrototypeOf() {
			We();
		}
	});
}
var Yt, Xt, Zt, Qt;
function $t() {
	if (Yt === void 0) {
		Yt = window, Xt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Zt = d(t, "firstChild").get, Qt = d(t, "nextSibling").get, g(e) && (e[ve] = void 0, e[_e] = null, e[ye] = void 0, e.__e = void 0), g(n) && (n[be] = void 0);
	}
}
function en(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function tn(e) {
	return Zt.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function F(e) {
	return Qt.call(e);
}
function I(e, t) {
	if (!S) return /* @__PURE__ */ tn(e);
	var n = /* @__PURE__ */ tn(C);
	if (n === null) n = C.appendChild(en());
	else if (t && n.nodeType !== 3) {
		var r = en();
		return n?.before(r), w(r), r;
	}
	return t && sn(n), w(n), n;
}
function nn(e, t = !1) {
	if (!S) return /* @__PURE__ */ tn(e);
	var n = I(e, t);
	return T(e), n;
}
function L(e, t = 1, n = !1) {
	let r = S ? C : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ F(r);
	if (!S) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = en();
			return r === null ? i?.after(a) : r.before(a), w(a), a;
		}
		sn(r);
	}
	return w(r), r;
}
function rn(e) {
	e.textContent = "";
}
function an() {
	return !1;
}
function on(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function sn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
function cn(e) {
	var t = K;
	if (t === null) return U.f |= fe, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	R(e, t);
}
function R(e, t) {
	if (!(t !== null && t.f & 16384)) {
		for (; t !== null;) {
			if (t.f & 128 && !(t.f & 33570816)) {
				if (!(t.f & 32768)) throw e;
				try {
					t.b.error(e);
					return;
				} catch (t) {
					e = t;
				}
			}
			t = t.parent;
		}
		throw e;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function ln(e) {
	K === null && (U === null && ze(e), Re()), H && Le(e);
}
function un(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function z(e, t) {
	var n = K;
	n !== null && n.f & 8192 && (e |= ne);
	var r = {
		ctx: E,
		deps: null,
		nodes: null,
		f: e | b | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	k?.register_created_effect(r);
	var i = r;
	if (e & 4) kt === null ? Nt.ensure().schedule(r) : kt.push(r);
	else if (t !== null) {
		try {
			Yn(r);
		} catch (e) {
			throw V(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= oe));
	}
	if (i !== null && (i.parent = n, n !== null && un(i, n), U !== null && U.f & 2 && !(e & 64))) {
		var a = U;
		(a.effects ??= []).push(i);
	}
	return r;
}
function dn() {
	return U !== null && !W;
}
function fn(e) {
	let t = z(8, null);
	return O(t, y), t.teardown = e, t;
}
function pn(e) {
	ln("$effect");
	var t = K.f;
	if (!U && t & 32 && E !== null && !E.i) {
		var n = E;
		(n.e ??= []).push(e);
	} else return mn(e);
}
function mn(e) {
	return z(4 | ce, e);
}
function hn(e) {
	return ln("$effect.pre"), z(8 | ce, e);
}
function gn(e) {
	Nt.ensure();
	let t = z(64 | se, e);
	return () => {
		V(t);
	};
}
function _n(e) {
	Nt.ensure();
	let t = z(64 | se, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? On(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function vn(e) {
	return z(4, e);
}
function yn(e) {
	return z(de | se, e);
}
function bn(e, t = 0) {
	return z(8 | t, e);
}
function xn(e, t = [], n = [], r = []) {
	dt(r, t, n, (t) => {
		z(8, () => {
			e(...t.map(Q));
		});
	});
}
function Sn(e, t = 0) {
	return z(16 | t, e);
}
function B(e) {
	return z(32 | se, e);
}
function Cn(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = H, r = U;
		Fn(!0), G(null);
		try {
			t.call(null);
		} catch (t) {
			R(t, e.parent);
		} finally {
			Fn(n), G(r);
		}
	}
}
function wn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && lt(() => {
			e.abort(Se);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function Tn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (En(e.nodes.start, e.nodes.end), n = !0), e.f |= ae, wn(e, t && !n), Jn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Cn(e), e.f ^= ae, e.f |= re;
	var i = e.parent;
	i !== null && i.first !== null && Dn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function En(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ F(e);
		e.remove(), e = n;
	}
}
function Dn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function On(e, t, n = !0) {
	var r = [];
	e.f |= 256, kn(e, r, !0);
	var i = () => {
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function kn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ne;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = !!(i.f & 65536) || !!(i.f & 32) && !!(e.f & 16);
				kn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function An(e) {
	e.f &= -257, jn(e, !0);
}
function jn(e, t) {
	if (!(e.f & 256) && e.f & 8192) {
		e.f ^= ne, e.f & 1024 || (O(e, b), Nt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = !!(n.f & 65536) || !!(n.f & 32);
			jn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Mn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ F(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Nn = null, Pn = !1, H = !1;
function Fn(e) {
	H = e;
}
var U = null, W = !1;
function G(e) {
	U = e;
}
var K = null;
function q(e) {
	K = e;
}
var J = null;
function In(e) {
	U !== null && (J ??= /* @__PURE__ */ new Set()).add(e);
}
var Y = null, X = 0, Z = null;
function Ln(e) {
	Z = e;
}
var Rn = 1, zn = 0, Bn = zn;
function Vn(e) {
	Bn = e;
}
function Hn() {
	return ++Rn;
}
function Un(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~le), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Un(a) && xt(a), a.wv > e.wv) return !0;
		}
		t & 512 && A === null && O(e, y);
	}
	return !1;
}
function Wn(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(J !== null && J.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? Wn(a, t, !1) : t === a && (n ? O(a, b) : a.f & 1024 && O(a, x), Lt(a));
	}
}
function Gn(e) {
	var t = Y, n = X, r = Z, i = U, a = J, o = E, s = W, c = Bn, l = e.f;
	Y = null, X = 0, Z = null, U = l & 96 ? null : e, J = null, qe(e.ctx), W = !1, Bn = ++zn, e.ac !== null && (lt(() => {
		e.ac.abort(Se);
	}), e.ac = null);
	try {
		e.f |= ue;
		var u = e.fn, d = u();
		e.f |= ie;
		var f = Kn(e);
		if (Ze() && Z !== null && !W && f !== null && !(e.f & 6146)) for (var p = 0; p < Z.length; p++) Wn(Z[p], e);
		if (i !== null && i !== e) {
			if (zn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = zn;
			if (t !== null) for (let e of t) e.rv = zn;
			Z !== null && (r === null ? r = Z : r.push(...Z));
		}
		return e.f & 8388608 && (e.f ^= fe), d;
	} catch (t) {
		return Kn(e), cn(t);
	} finally {
		e.f ^= ue, Y = t, X = n, Z = r, U = i, J = a, qe(o), W = s, Bn = c;
	}
}
function Kn(e) {
	var t = e.deps, n = k?.is_fork;
	if (Y !== null) {
		var r;
		if (n || Jn(e, X), t !== null && X > 0) for (t.length = X + Y.length, r = 0; r < Y.length; r++) t[X + r] = Y[r];
		else e.deps = t = Y;
		if (dn() && e.f & 512) for (r = X; r < t.length; r++) (t[r].reactions ??= []).push(e);
	} else !n && t !== null && X < t.length && (Jn(e, X), t.length = X);
	return t;
}
function qn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var i = o.call(n, e);
		if (i !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[i] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (Y === null || !s.call(Y, t))) {
		var c = t;
		c.f & 512 && (c.f ^= 512, c.f &= ~le), c.v !== r && nt(c), c.ac !== null && lt(() => {
			c.ac.abort(Se), c.ac = null, O(c, b);
		}), St(c), Jn(c, 0);
	}
}
function Jn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) qn(e, n[r]);
}
function Yn(e) {
	var t = e.f;
	if (!(t & 16384)) {
		O(e, y);
		var n = K, r = Pn;
		K = e, Pn = !(t & 96);
		try {
			t & 16777232 ? Tn(e) : wn(e), Cn(e);
			var i = Gn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Rn;
		} finally {
			Pn = r, K = n;
		}
	}
}
async function Xn() {
	await Promise.resolve(), Pt();
}
function Q(e) {
	var t = !!(e.f & 2);
	if (Nn?.add(e), U !== null && !W && !(K !== null && K.f & 16384) && (J === null || !J.has(e))) {
		var n = U.deps;
		if (U.f & 2097152) e.rv < zn && (e.rv = zn, Y === null && n !== null && n[X] === e ? X++ : Y === null ? Y = [e] : Y.push(e));
		else {
			U.deps ??= [], s.call(U.deps, e) || U.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [U] : s.call(r, U) || r.push(U);
		}
	}
	if (H && M.has(e)) return M.get(e);
	if (t) {
		var i = e;
		if (H) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || Qn(i)) && (a = bt(i)), M.set(i, a), a;
		}
		var o = !(i.f & 512) && !W && U !== null && (Pn || !!(U.f & 512)), c = (i.f & ie) === 0;
		Un(i) && (o && (i.f |= 512), xt(i)), o && !c && (Ct(i), Zn(i));
	}
	if (A?.has(e)) return A.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function Zn(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Ct(t), Zn(t));
}
function Qn(e) {
	if (e.v === r) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (M.has(t) || t.f & 2 && Qn(t)) return !0;
	return !1;
}
function $n(e) {
	var t = W;
	try {
		return W = !0, e();
	} finally {
		W = t;
	}
}
function er(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (pe in e) tr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && pe in n && tr(n);
		}
	}
}
function tr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			tr(e[n], t);
		} catch {}
		let n = h(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = f(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var nr = Symbol("events"), rr = /* @__PURE__ */ new Set(), ir = /* @__PURE__ */ new Set();
function ar(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || lr.call(t, e), !e.cancelBubble) return lt(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? D(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function or(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = ar(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && fn(() => {
		t.removeEventListener(e, o, a);
	});
}
var sr = null, cr = !1;
function lr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	sr = e, cr || (cr = !0, setTimeout(() => {
		cr = !1, sr = null;
	}));
	var o = 0, s = sr === e && e[nr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[nr] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		u(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var d = U, f = K;
		G(null), q(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[nr]?.[r];
					h != null && (!a.disabled || e.target === a) && h.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble) break;
				o++, a = o < i.length ? i[o] : null;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[nr] = t, delete e.currentTarget, G(d), q(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var ur = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function dr(e) {
	return ur?.createHTML(e) ?? e;
}
function fr(e) {
	var t = on("template");
	return t.innerHTML = dr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function pr(e, t) {
	var n = K;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function mr(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (S) return pr(C, null), C;
		i === void 0 && (i = fr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ tn(i)));
		var t = r || Xt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ tn(t), s = t.lastChild;
			pr(o, s);
		} else pr(t, t);
		return t;
	};
}
function $(e, t) {
	if (S) {
		var n = K;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = C), Oe();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var hr = ["touchstart", "touchmove"];
function gr(e) {
	return hr.includes(e);
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function _r(e) {
	let t = 0, n = Ht(0), r;
	return () => {
		dn() && (Q(n), bn(() => (t === 0 && (r = $n(() => e(() => Kt(n)))), t += 1, () => {
			D(() => {
				--t, t === 0 && (r?.(), r = void 0, Kt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var vr = oe | se;
function yr(e, t, n, r) {
	new br(e, t, n, r);
}
var br = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = S ? C : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = _r(() => (this.#m = Ht(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = K;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = K.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Sn(() => {
			if (S) {
				let e = this.#t;
				Oe();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#y() : this.#g();
			} else this.#b();
		}, vr), S && (this.#e = C);
	}
	#g() {
		try {
			this.#a = B(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#v(e);
		D(r), t && (this.#s = B(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#v(e) {
		var t = !1, n = !1;
		let r = () => {
			if (t) {
				Ee();
				return;
			}
			t = !0, n && Ke(), this.#s !== null && On(this.#s, () => {
				this.#s = null;
			}), this.#S(() => {
				this.#b();
			});
		};
		return {
			reset: r,
			invoke_onerror: () => {
				try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					R(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = B(() => e(this.#e)), D(() => {
			var e = this.#c = document.createDocumentFragment(), t = en(), n = !1;
			if (e.append(t), this.#a = this.#S(() => {
				try {
					return B(() => this.#r(t));
				} catch (e) {
					try {
						this.error(e), n = !0;
					} catch (e) {
						R(e, this.#i.parent);
					}
					return null;
				}
			}), this.#a === null) {
				this.#c = null, n && this.#x(k);
				return;
			}
			this.#u === 0 && (this.#e.before(e), this.#c = null, On(this.#o, () => {
				this.#o = null;
			}), this.#x(k));
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = B(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Mn(this.#a, e);
				let t = this.#n.pending;
				this.#o = B(() => t(this.#e));
			} else this.#x(k);
		} catch (e) {
			this.error(e);
		}
	}
	#x(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		it(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#S(e) {
		var t = K, n = U, r = E;
		q(this.#i), G(this.#i), qe(this.#i.ctx);
		try {
			return Nt.ensure(), e();
		} finally {
			q(t), G(n), qe(r);
		}
	}
	#C(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#C(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#x(t), this.#o && On(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#C(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, D(() => {
			this.#d = !1, this.#m && Wt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Q(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		k?.is_fork ? (this.#a && k.skip_effect(this.#a), this.#o && k.skip_effect(this.#o), this.#s && k.skip_effect(this.#s), k.oncommit(() => {
			this.#w(e);
		})) : this.#w(e);
	}
	#w(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), S && (w(this.#t), ke(), w(Ae()));
		let t = this.#n.failed, n = (e) => {
			let { reset: n, invoke_onerror: r } = this.#v(e);
			r(), t && (this.#s = this.#S(() => {
				try {
					return B(() => {
						var r = K;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return R(e, this.#i.parent), null;
				}
			}));
		};
		D(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				R(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => R(e, this.#i && this.#i.parent)) : n(t);
		});
	}
};
function xr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[be] ??= e.nodeValue) && (e[be] = n, e.nodeValue = `${n}`);
}
function Sr(e, t) {
	return Tr(e, t);
}
function Cr(e, t) {
	$t(), t.intro = t.intro ?? !1;
	let r = t.target, i = S, a = C;
	try {
		for (var o = /* @__PURE__ */ tn(r); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ F(o);
		if (!o) throw n;
		De(!0), w(o);
		let i = Tr(e, {
			...t,
			anchor: o
		});
		return De(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== n && console.warn("Failed to hydrate: ", i), t.recover === !1 && Ve(), $t(), rn(r), De(!1), Sr(e, t);
	} finally {
		De(i), w(a);
	}
}
var wr = /* @__PURE__ */ new Map();
function Tr(e, { target: t, anchor: r, props: i = {}, events: a, context: o, intro: s = !0, transformError: l }) {
	$t();
	var u = void 0, d = _n(() => {
		var s = r ?? t.appendChild(en());
		yr(s, { pending: () => {} }, (t) => {
			Je({});
			var r = E;
			if (o && (r.c = o), a && (i.$$events = a), S && pr(t, null), u = e(t, i) || Xe(), S && (K.nodes.end = C, C === null || C.nodeType !== 8 || C.data !== "]")) throw Te(), n;
			Ye();
		}, l);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = gr(r);
					for (let e of [t, document]) {
						var a = wr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), wr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, lr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(c(rr)), ir.add(f), () => {
			for (var e of d) for (let r of [t, document]) {
				var n = wr.get(r), i = n.get(e);
				--i == 0 ? (r.removeEventListener(e, lr), n.delete(e), n.size === 0 && wr.delete(r)) : n.set(e, i);
			}
			ir.delete(f), s !== r && s.parentNode?.removeChild(s);
		};
	});
	return Er.set(u, d), u;
}
var Er = /* @__PURE__ */ new WeakMap();
function Dr(e, t) {
	let n = Er.get(e);
	return n ? (Er.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Or = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) An(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (An(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (V(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Mn(r, t), t.append(en()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), On(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = k, r = an();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = document.createDocumentFragment(), a = en();
				i.append(a), this.#n.set(e, {
					effect: B(() => t(a)),
					fragment: i
				});
			} else this.#t.set(e, B(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else S && (this.anchor = C), this.#a(n);
	}
};
function kr(t) {
	E === null && Fe("onMount"), e && E.l !== null ? Ar(E).m.push(t) : pn(() => {
		let e = $n(t);
		if (typeof e == "function") return e;
	});
}
function Ar(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function jr(e, t, n = !1) {
	var r;
	S && (r = C, Oe());
	var i = new Or(e), a = n ? oe : 0;
	function o(e, t) {
		if (S) {
			var n = je(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Ae();
				w(a), i.anchor = a, De(!1), i.ensure(e, t), De(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	Sn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Mr(e, t) {
	vn(() => {
		e = K?.parent?.nodes?.start ?? e;
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = on("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Nr = Symbol("is custom element"), Pr = Symbol("is html"), Fr = Ce ? "link" : "LINK";
function Ir(e) {
	if (S) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Lr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Lr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[xe] = n, D(n), ct();
	}
}
function Lr(e, t, n, r) {
	var i = Rr(e);
	S && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Fr) || i[t] !== (i[t] = n) && (t === "loading" && (e[ge] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Br(e).has(t) ? e[t] = n : e.setAttribute(t, n));
}
function Rr(e) {
	return e[_e] ??= {
		[Nr]: e.nodeName.includes("-"),
		[Pr]: e.namespaceURI === i
	};
}
var zr = /* @__PURE__ */ new Map();
function Br(e) {
	var t = e.getAttribute("is") || e.nodeName, n = zr.get(t);
	if (n) return n;
	zr.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = f(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.add(o);
		i = h(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Vr(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	ut(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = Hr(e) ? Ur(a) : a, n(a), k !== null && r.add(k), await Xn(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (S && e.defaultValue !== e.value || $n(t) == null && e.value) && (n(Hr(e) ? Ur(e.value) : e.value), k !== null && r.add(k)), bn(() => {
		var n = t();
		if (e === document.activeElement) {
			var i = k;
			if (r.has(i)) return;
		}
		Hr(e) && n === Ur(e.value) || (e.type !== "date" || n || e.value) && n !== e.value && (e.value = n ?? "");
	});
}
function Hr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Ur(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Wr(e = !1) {
	let t = E, n = t.l.u;
	if (!n) return;
	let r = () => er(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ ht(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Q(i);
	}
	n.b.length && hn(() => {
		Gr(t, r), _(n.b);
	}), pn(() => {
		let e = $n(() => n.m.map(te));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && pn(() => {
		Gr(t, r), _(n.a);
	});
}
function Gr(e, t) {
	if (e.l.s) for (let t of e.l.s) Q(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function Kr(t, n, r, i) {
	var a = !e || !!(r & 2), o = !!(r & 8), s = !!(r & 16), c = i, l = !0, u = void 0, f = () => s && a ? (u ??= /* @__PURE__ */ ht(i), Q(u)) : (l && (l = !1, c = s ? $n(i) : i), c);
	let p;
	if (o) {
		var m = pe in t || he in t;
		p = d(t, n)?.set ?? (m && n in t ? (e) => t[n] = e : void 0);
	}
	var h, g = !1;
	o ? [h, g] = ot(() => t[n]) : h = t[n], h === void 0 && i !== void 0 && (h = f(), p && (a && He(n), p(h)));
	var ee = a ? () => {
		var e = t[n];
		return e === void 0 ? f() : (l = !0, e);
	} : () => {
		var e = t[n];
		return e !== void 0 && (c = void 0), e === void 0 ? c : e;
	};
	if (a && !(r & 4)) return ee;
	if (p) {
		var te = t.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || te || g) && p(t ? ee() : e), e) : ee();
		});
	}
	var _ = !1, v = (r & 1 ? ht : vt)(() => (_ = !1, ee()));
	o && Q(v);
	var y = K;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Q(v) : a && o ? Jt(e) : e;
			return P(v, n), _ = !0, c !== void 0 && (c = n), e;
		}
		return H && _ || y.f & 16384 ? v.v : Q(v);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function qr(e) {
	return new Jr(e);
}
var Jr = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ N(n, !1, !1);
			return t.set(e, r), r;
		};
		let r = new Proxy({
			...e.props || {},
			$$events: {}
		}, {
			get(e, r) {
				return Q(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === he || (Q(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return P(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		});
		this.#t = (e.hydrate ? Cr : Sr)(e.component, {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		}), (!e?.props?.$$host || e.sync === !1) && Pt(), this.#e = r.$$events;
		for (let e of Object.keys(this.#t)) e !== "$set" && e !== "$destroy" && e !== "$on" && u(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(r, e);
		}, this.#t.$destroy = () => {
			Dr(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, Yr;
typeof HTMLElement == "function" && (Yr = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = on("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = Zr(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = Xr(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = qr({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = gn(() => {
				bn(() => {
					this.$$r = !0;
					for (let e of l(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = Xr(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = Xr(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return l(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function Xr(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function Zr(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function Qr(e, t, n, r, i, a) {
	let o = class extends Yr {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return l(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return l(t).forEach((e) => {
		u(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = Xr(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (d(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		u(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region JellyfinCard.svelte
var $r = /* @__PURE__ */ mr("<span class=\"status-badge active svelte-1uhbaav\">● Active</span>"), ei = /* @__PURE__ */ mr("<span class=\"status-badge success svelte-1uhbaav\">✓ Authenticated</span>"), ti = /* @__PURE__ */ mr("<span class=\"status-badge success svelte-1uhbaav\">● Connected</span>"), ni = /* @__PURE__ */ mr("<span class=\"status-badge warning svelte-1uhbaav\">⚠ Disconnected</span>"), ri = /* @__PURE__ */ mr("<div class=\"loading-state svelte-1uhbaav\">Loading...</div>"), ii = /* @__PURE__ */ mr("<button class=\"btn-ghost svelte-1uhbaav\"> </button>"), ai = /* @__PURE__ */ mr("<div class=\"settings-section svelte-1uhbaav\"><h3 class=\"section-title svelte-1uhbaav\">Server Configuration</h3> <div class=\"form-grid svelte-1uhbaav\"><label class=\"form-field svelte-1uhbaav\"><span class=\"field-label svelte-1uhbaav\">Server URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:8096\" class=\"input-field svelte-1uhbaav\"/> <span class=\"helper-text svelte-1uhbaav\">Enter your Jellyfin server URL (include port, typically :8096)</span></label> <label class=\"form-field svelte-1uhbaav\"><span class=\"field-label svelte-1uhbaav\">Username</span> <input type=\"text\" placeholder=\"Enter username\" class=\"input-field svelte-1uhbaav\"/></label> <label class=\"form-field svelte-1uhbaav\"><span class=\"field-label svelte-1uhbaav\">Password</span> <div class=\"password-wrapper svelte-1uhbaav\"><input class=\"input-field svelte-1uhbaav\"/> <button type=\"button\" class=\"toggle-visibility svelte-1uhbaav\"> </button></div></label> <div class=\"actions-row svelte-1uhbaav\"><button class=\"btn-primary svelte-1uhbaav\"> </button> <!> <!></div></div></div>"), oi = /* @__PURE__ */ mr("<section class=\"plugin-card svelte-1uhbaav\"><div class=\"card-header svelte-1uhbaav\"><div class=\"header-left svelte-1uhbaav\"><h2 class=\"card-title svelte-1uhbaav\">Jellyfin</h2> <div class=\"badges svelte-1uhbaav\"><!> <!> <!></div></div> <button class=\"btn-ghost svelte-1uhbaav\"> </button></div> <!></section>"), si = {
	hash: "svelte-1uhbaav",
	code: ".plugin-card.svelte-1uhbaav {background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:var(--radius, 16px);padding:28px;color:var(--text-primary);font-family:\"Inter\", sans-serif;box-shadow:0 4px 24px rgba(0, 0, 0, 0.2);}.card-header.svelte-1uhbaav {display:flex;justify-content:space-between;align-items:center;margin-bottom:28px;padding-bottom:20px;border-bottom:1px solid var(--border-subtle);}.header-left.svelte-1uhbaav {display:flex;align-items:center;gap:16px;}.card-title.svelte-1uhbaav {margin:0;font-size:22px;font-weight:800;letter-spacing:-0.02em;background:linear-gradient(135deg, #fff 0%, #a5b4fc 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}.badges.svelte-1uhbaav {display:flex;gap:8px;}.status-badge.svelte-1uhbaav {font-size:10px;padding:3px 10px;border-radius:6px;font-weight:800;text-transform:uppercase;letter-spacing:0.03em;}.status-badge.active.svelte-1uhbaav {background:rgba(20, 184, 166, 0.1);color:var(--color-primary);border:1px solid rgba(20, 184, 166, 0.2);}.status-badge.success.svelte-1uhbaav {background:rgba(16, 185, 129, 0.1);color:#10b981;border:1px solid rgba(16, 185, 129, 0.2);}.status-badge.warning.svelte-1uhbaav {background:rgba(245, 158, 11, 0.1);color:#f59e0b;border:1px solid rgba(245, 158, 11, 0.2);}.btn-ghost.svelte-1uhbaav {padding:10px 18px;background:rgba(255, 255, 255, 0.05);border:1px solid var(--border-subtle);color:var(--text-primary);border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;transition:all 0.2s ease;}.btn-ghost.svelte-1uhbaav:hover {background:rgba(255, 255, 255, 0.1);border-color:rgba(255, 255, 255, 0.2);transform:translateY(-1px);}.btn-primary.svelte-1uhbaav {padding:12px 28px;background:var(--color-primary);color:#000;border:none;border-radius:12px;font-weight:700;font-size:14px;cursor:pointer;transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1);box-shadow:0 4px 12px rgba(20, 184, 166, 0.2);}.btn-primary.svelte-1uhbaav:hover:not(:disabled) {filter:brightness(1.1);transform:translateY(-2px);box-shadow:0 6px 20px rgba(20, 184, 166, 0.3);}.btn-primary.svelte-1uhbaav:disabled {opacity:0.4;cursor:not-allowed;}.loading-state.svelte-1uhbaav {display:flex;flex-direction:column;align-items:center;gap:20px;padding:60px;color:var(--text-muted);}.settings-section.svelte-1uhbaav {margin-top:24px;}.section-title.svelte-1uhbaav {margin:0 0 20px 0;font-size:14px;font-weight:700;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;}.form-grid.svelte-1uhbaav {display:grid;grid-template-columns:1fr;gap:20px;}\n\n  @media (min-width: 640px) {.form-grid.svelte-1uhbaav {grid-template-columns:1fr 1fr;}\n  }.form-field.svelte-1uhbaav {display:flex;flex-direction:column;gap:10px;}.field-label.svelte-1uhbaav {font-size:12px;font-weight:600;color:var(--text-secondary);opacity:0.8;}.input-field.svelte-1uhbaav {width:100%;padding:14px 18px;background:var(--bg-input, #0f172a);border:1px solid var(--border-subtle);border-radius:12px;color:var(--text-primary);font-size:14px;transition:all 0.25s cubic-bezier(0.4, 0, 0.2, 1);}.input-field.svelte-1uhbaav:focus {outline:none;border-color:var(--color-primary);box-shadow:0 0 0 4px rgba(20, 184, 166, 0.15);background:rgba(255, 255, 255, 0.03);}.password-wrapper.svelte-1uhbaav {position:relative;display:flex;align-items:center;}.toggle-visibility.svelte-1uhbaav {position:absolute;right:14px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary);font-size:18px;padding:0;display:flex;align-items:center;justify-content:center;}.toggle-visibility.svelte-1uhbaav:hover {opacity:1;}.helper-text.svelte-1uhbaav {font-size:11px;color:var(--text-muted);margin-top:6px;font-style:italic;}.actions-row.svelte-1uhbaav {display:flex;gap:16px;flex-wrap:wrap;margin-top:12px;}"
};
function ci(e, t) {
	Je(t, !1), Mr(e, si);
	let n = Kr(t, "apiBase", 12, ""), r = /* @__PURE__ */ N(""), i = /* @__PURE__ */ N(""), a = /* @__PURE__ */ N(""), o = /* @__PURE__ */ N(!1), s = /* @__PURE__ */ N(!1), c = /* @__PURE__ */ N(!0), l = /* @__PURE__ */ N(!1), u = /* @__PURE__ */ N(!1), d = /* @__PURE__ */ N(!1), f = /* @__PURE__ */ N(!1), p = /* @__PURE__ */ N(!1), m = /* @__PURE__ */ N(!1);
	kr(async () => {
		await g(), P(c, !1);
	});
	async function h() {
		try {
			P(m, !0), await fetch(`${n()}/activate`, { method: "POST" }), await g();
		} catch (e) {
			console.error("Failed to activate server:", e);
		} finally {
			P(m, !1);
		}
	}
	async function g() {
		try {
			let e = await (await fetch(`${n()}/settings`)).json();
			e?.settings && (P(r, e.settings.base_url || ""), P(i, e.settings.username || ""), P(o, e.settings.has_password || !1), P(s, e.settings.connected || !1), P(p, e.settings.is_active || !1), P(a, ""));
		} catch (e) {
			console.error("Failed to load Jellyfin settings:", e);
		}
	}
	async function ee() {
		if (!Q(r).trim()) {
			console.error("Server URL is required");
			return;
		}
		if (!Q(i).trim() || !Q(o) && !Q(a).trim()) {
			console.error("Username and password are required");
			return;
		}
		try {
			P(l, !0), await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					base_url: Q(r),
					username: Q(i),
					password: Q(a)
				})
			}), await g();
		} catch (e) {
			console.error("Failed to save Jellyfin settings:", e);
		} finally {
			P(l, !1);
		}
	}
	async function te() {
		try {
			P(u, !0), (await (await fetch(`${n()}/test-connection`, { method: "POST" })).json())?.connected && await g();
		} catch (e) {
			console.error("Connection test failed:", e);
		} finally {
			P(u, !1);
		}
	}
	var _ = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Pt();
		}
	};
	Wr();
	var v = oi(), y = I(v), b = I(y), x = L(I(b), 2), ne = I(x), re = (e) => {
		$(e, $r());
	};
	jr(ne, (e) => {
		Q(p) && e(re);
	});
	var ie = L(ne, 2), ae = (e) => {
		$(e, ei());
	};
	jr(ie, (e) => {
		Q(o) && e(ae);
	});
	var oe = L(ie, 2), se = (e) => {
		$(e, ti());
	}, ce = (e) => {
		$(e, ni());
	};
	jr(oe, (e) => {
		Q(s) ? e(se) : Q(o) && e(ce, 1);
	}), T(x), T(b);
	var le = L(b, 2), ue = nn(le, !0);
	T(y);
	var de = L(y, 2), fe = (e) => {
		$(e, ri());
	}, pe = (e) => {
		var t = ai(), n = L(I(t), 2), s = I(n), c = L(I(s), 2);
		Ir(c), ke(2), T(s);
		var d = L(s, 2), g = L(I(d), 2);
		Ir(g), T(d);
		var _ = L(d, 2), v = L(I(_), 2), y = I(v);
		Ir(y);
		var b = L(y, 2), x = nn(b, !0);
		T(v), T(_);
		var ne = L(_, 2), re = I(ne), ie = nn(re, !0), ae = L(re, 2), oe = (e) => {
			var t = ii(), n = nn(t, !0);
			xn(() => {
				t.disabled = Q(u), xr(n, Q(u) ? "Testing..." : "Test Connection");
			}), or("click", t, te), $(e, t);
		};
		jr(ae, (e) => {
			Q(o) && e(oe);
		});
		var se = L(ae, 2), ce = (e) => {
			var t = ii(), n = nn(t, !0);
			xn(() => {
				t.disabled = Q(m), xr(n, Q(m) ? "Activating..." : "Activate Server");
			}), or("click", t, h), $(e, t);
		};
		jr(se, (e) => {
			Q(p) || e(ce);
		}), T(ne), T(n), T(t), xn(() => {
			Lr(y, "type", Q(f) ? "text" : "password"), Lr(y, "placeholder", Q(o) ? "••••••••" : "Enter password"), xr(x, Q(f) ? "🙈" : "👁️"), re.disabled = Q(l), xr(ie, Q(l) ? "Saving..." : "Save Settings");
		}), Vr(c, () => Q(r), (e) => P(r, e)), Vr(g, () => Q(i), (e) => P(i, e)), Vr(y, () => Q(a), (e) => P(a, e)), or("click", b, () => P(f, !Q(f))), or("click", re, ee), $(e, t);
	};
	return jr(de, (e) => {
		Q(c) ? e(fe) : Q(d) || e(pe, 1);
	}), T(v), xn(() => xr(ue, Q(d) ? "Expand" : "Collapse")), or("click", le, () => P(d, !Q(d))), $(e, v), Ye(_);
}
customElements.define("jellyfin-dashboard-card", Qr(ci, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { ci as default };

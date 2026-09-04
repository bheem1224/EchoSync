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
var n = {}, r = Symbol("uninitialized"), i = "http://www.w3.org/1999/xhtml", a = Array.isArray, o = Array.prototype.indexOf, s = Array.prototype.includes, c = Array.from, l = Object.keys, u = Object.defineProperty, d = Object.getOwnPropertyDescriptor, f = Object.getOwnPropertyDescriptors, p = Object.prototype, m = Array.prototype, h = Object.getPrototypeOf, ee = Object.isExtensible, g = () => {};
function _(e) {
	return e();
}
function v(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function y() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var b = 1024, x = 2048, S = 4096, te = 8192, C = 16384, ne = 32768, re = 1 << 25, ie = 65536, ae = 1 << 19, oe = 1 << 20, se = 65536, ce = 1 << 21, le = 1 << 22, ue = 1 << 23, de = Symbol("$state"), fe = Symbol("component"), pe = Symbol("legacy props"), me = Symbol(""), he = Symbol("attributes"), ge = Symbol("class"), _e = Symbol("style"), ve = Symbol("text"), ye = Symbol("form reset"), be = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), xe = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function Se() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Ce(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function we() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var w = !1;
function Te(e) {
	w = e;
}
var T;
function E(e) {
	if (e === null) throw Ce(), n;
	return T = e;
}
function Ee() {
	return E(/* @__PURE__ */ F(T));
}
function D(e) {
	if (w) {
		if (/* @__PURE__ */ F(T) !== null) throw Ce(), n;
		T = e;
	}
}
function De(e = 1) {
	if (w) {
		for (var t = e, n = T; t--;) n = /* @__PURE__ */ F(n);
		T = n;
	}
}
function Oe(e = !0) {
	for (var t = 0, n = T;;) {
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
function ke(e) {
	if (!e || e.nodeType !== 8) throw Ce(), n;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Ae(e) {
	return e === this.v;
}
function je(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Me(e) {
	return !je(e, this.v);
}
function Ne(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function Pe() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Fe(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Ie() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Le(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Re() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function ze() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Be(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Ve() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function He() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Ue() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function We() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var O = null;
function Ge(e) {
	O = e;
}
function Ke(t, n = !1, r) {
	O = {
		p: O,
		i: !1,
		c: null,
		e: null,
		s: t,
		x: null,
		r: W,
		l: e && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function qe(e) {
	var t = O, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) hn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, O = t.p, Je(e);
}
function Je(e = {}) {
	return u(e, fe, { value: !0 }), e;
}
function Ye() {
	return !e || O !== null && O.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Xe = [];
function Ze() {
	var e = Xe;
	Xe = [], v(e);
}
function Qe(e) {
	if (Xe.length === 0 && !Et) {
		var t = Xe;
		queueMicrotask(() => {
			t === Xe && Ze();
		});
	}
	Xe.push(e);
}
function $e() {
	for (; Xe.length > 0;) Ze();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var et = ~(x | S | b);
function k(e, t) {
	e.f = e.f & et | t;
}
function tt(e) {
	e.f & 512 || e.deps === null ? k(e, b) : k(e, S);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function nt(e) {
	if (e !== null) for (let t of e) t.f & 2 && t.f & 65536 && (t.f ^= se, nt(t.deps));
}
function rt(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), nt(e.deps), k(e, b);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var it = !1;
function at(e) {
	var t = it;
	try {
		return it = !1, [e(), it];
	} finally {
		it = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var ot = !1;
function st() {
	ot || (ot = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ye]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function ct(e) {
	var t = V, n = W;
	U(null), G(null);
	try {
		return e();
	} finally {
		U(t), G(n);
	}
}
function lt(e, t, n, r = n) {
	e.addEventListener(t, () => ct(n));
	let i = e[ye];
	e[ye] = i ? () => {
		i(), r(!0);
	} : () => r(!0), st();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function ut(e, t, n, r) {
	let i = Ye() ? mt : _t;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = W, c = dt(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				R(e, s);
			}
			ft();
		}
	}
	var d = pt();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ gt(e))).then(u).catch((e) => R(e, s)).finally(d);
	}
	l ? l.then(() => {
		c(), f(), ft();
	}) : f();
}
function dt() {
	var e = W, t = V, n = O, r = A;
	return function(i = !0) {
		G(e), U(t), Ge(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function ft(e = !0) {
	G(null), U(null), Ge(null), e && A?.deactivate();
}
function pt() {
	var e = W, t = e.b, n = A, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function mt(e) {
	var t = 2 | x;
	return W !== null && (W.f |= ae), {
		ctx: O,
		deps: null,
		effects: null,
		equals: Ae,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: r,
		wv: 0,
		parent: W,
		ac: null
	};
}
var ht = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function gt(e, t, n) {
	let i = W;
	i === null && Pe();
	var a = void 0, o = Ht(r), s = !V, c = /* @__PURE__ */ new Set();
	return bn(() => {
		var t = W, n = y();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== be && n.reject(e);
			}).finally(ft);
		} catch (e) {
			n.reject(e), ft();
		}
		var r = A;
		if (s) {
			if (t.f & 32768) var l = pt();
			if (i.b?.is_rendered()) r.async_deriveds.get(t)?.reject(ht);
			else for (let e of c.values()) e.reject(ht);
			c.add(n), r.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== ht && (r.activate(), t ? (o.f |= ue, Wt(o, t)) : (o.f & 8388608 && (o.f ^= ue), Wt(o, e)), r.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), pn(() => {
		for (let e of c) e.reject(ht);
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
function _t(e) {
	let t = /* @__PURE__ */ mt(e);
	return t.equals = Me, t;
}
function vt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) B(t[n]);
	}
}
function yt(e) {
	var t, n = W, i = e.parent;
	if (!Ln && i !== null && e.v !== r && i.f & 24576) return Se(), e.v;
	G(i);
	try {
		e.f &= ~se, vt(e), t = Jn(e);
	} finally {
		G(n);
	}
	return t;
}
function bt(e) {
	var t = yt(e);
	if (!e.equals(t) && (e.wv = Gn(), (!A?.is_fork || e.deps === null) && (A === null ? e.v = t : (A.capture(e, t, !0), wt?.capture(e, t, !0)), e.deps === null))) {
		k(e, b);
		return;
	}
	Ln || (j === null ? tt(e) : (fn() || A?.is_fork) && j.set(e, t));
}
function xt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && ct(() => {
		t.ac.abort(be), t.ac = null;
	}), t.fn !== null && (t.teardown = g), Zn(t, 0), En(t));
}
function St(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && Qn(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var Ct = null, A = null, wt = null, j = null, Tt = null, Et = !1, Dt = !1, Ot = null, kt = null, At = 0, jt = 1, Mt = class e {
	id = jt++;
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
		Ct === null ? Ct = this : (Ct.#n = this, this.#t = Ct), Ct = this;
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
			for (var r of n.d) k(r, x), t(r);
			for (r of n.m) k(r, S), t(r);
		}
		this.#p.add(e);
	}
	#g() {
		this.#e = !0, At++ > 1e3 && (this.#x(), Pt());
		for (let e of this.#u) this.#d.delete(e), k(e, x), this.schedule(e);
		for (let e of this.#d) k(e, S), this.schedule(e);
		let t = this.#c;
		this.#c = [], this.apply();
		var n = Ot = [], r = [], i = kt = [];
		for (let e of t) try {
			this.#_(e, n, r);
		} catch (t) {
			throw zt(e), this.#h() || this.discard(), t;
		}
		if (A = null, i.length > 0) {
			var a = e.ensure();
			for (let e of i) a.schedule(e);
		}
		if (Ot = null, kt = null, this.#h()) {
			this.#b(r), this.#b(n);
			for (let [e, t] of this.#f) Rt(e, t);
			i.length > 0 && A.#g();
			return;
		}
		let o = this.#v();
		if (o) {
			this.#b(r), this.#b(n), o.#y(this);
			return;
		}
		this.#u.clear(), this.#d.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), wt = this, It(r), It(n), wt = null, this.#s?.resolve();
		var s = A;
		if (this.#a === 0 && (this.#c.length === 0 || s !== null) && this.#x(), this.#c.length > 0) {
			if (s !== null) {
				let e = s;
				e.#c.push(...this.#c.filter((t) => !e.#c.includes(t)));
			} else s = this;
		}
		s !== null && (M.clear(), s.#g());
	}
	#_(e, t, n) {
		e.f ^= b;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = !!(i & 96);
			if (!(a && i & 1024 || i & 8192 || this.#f.has(r)) && r.fn !== null) {
				a ? r.f ^= b : i & 4 ? t.push(r) : Kn(r) && (i & 16 && this.#d.add(r), Qn(r));
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
					r & 4194320 && !this.async_deriveds.has(i) && (this.#d.delete(i), k(i, x), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#x(), A = this, this.#g();
	}
	#b(e) {
		for (var t = 0; t < e.length; t += 1) rt(e[t], this.#u, this.#d);
	}
	capture(e, t, n = !1) {
		e.v !== r && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), j?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		A = this;
	}
	deactivate() {
		A = null, j = null;
	}
	flush() {
		try {
			Dt = !0, A = this, this.#g();
		} finally {
			At = 0, Tt = null, Ot = null, kt = null, Dt = !1, A = null, j = null, M.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear();
		for (let e of this.async_deriveds.values()) e.reject(ht);
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
		this.#m || (this.#m = !0, Qe(() => {
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
		return (this.#s ??= y()).promise;
	}
	static ensure() {
		if (A === null) {
			let t = A = new e();
			!Dt && !Et && Qe(() => {
				t.#e || t.flush();
			});
		}
		return A;
	}
	apply() {
		j = null;
	}
	schedule(e) {
		if (Tt = e, e.b?.is_pending && e.f & 16777228 && !(e.f & 32768)) {
			e.b.defer_effect(e);
			return;
		}
		for (var t = e; t.parent !== null;) {
			t = t.parent;
			var n = t.f;
			if (Ot !== null && t === W && (V === null || !(V.f & 2))) return;
			if (n & 96) {
				if (!(n & 1024)) return;
				t.f ^= b;
			}
		}
		this.#c.push(t);
	}
	#x() {
		if (this.linked) {
			var e = this.#t, t = this.#n;
			e === null || (e.#n = t), t === null ? Ct = e : t.#t = e, this.linked = !1;
		}
	}
};
function Nt(e) {
	var t = Et;
	Et = !0;
	try {
		var n;
		for (e && (A !== null && !A.is_fork && A.flush(), n = e());;) {
			if ($e(), A === null) return n;
			A.flush();
		}
	} finally {
		Et = t;
	}
}
function Pt() {
	try {
		Re();
	} catch (e) {
		R(e, Tt);
	}
}
var Ft = null;
function It(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Kn(r) && (Ft = /* @__PURE__ */ new Set(), Qn(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && kn(r), Ft?.size > 0)) {
				M.clear();
				for (let e of Ft) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) Ft.has(n) && (Ft.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || Qn(n);
					}
				}
				Ft.clear();
			}
		}
		Ft = null;
	}
}
function Lt(e) {
	A.schedule(e);
}
function Rt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), k(e, b);
		for (var n = e.first; n !== null;) Rt(n, t), n = n.next;
	}
}
function zt(e) {
	k(e, b);
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
		equals: Ae,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Ut(e, t) {
	let n = Ht(e, t);
	return zn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function N(t, n = !1, r = !0) {
	let i = Ht(t);
	return n || (i.equals = Me), e && r && O !== null && O.l !== null && (O.l.s ??= []).push(i), i;
}
function P(e, t, n = !1) {
	return V !== null && (!H || V.f & 131072) && Ye() && V.f & 4325394 && (K === null || !K.has(e)) && Ue(), Wt(e, n ? Jt(t) : t, kt);
}
function Wt(e, t, n = null) {
	if (!e.equals(t)) {
		Ln ? M.set(e, t) : M.has(e) || M.set(e, e.v);
		var r = Mt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && yt(t), j === null && tt(t);
		}
		e.wv = Gn(), qt(e, x, n), Ye() && W !== null && W.f & 1024 && !(W.f & 96) && (Y === null ? Bn([e]) : Y.push(e)), !r.is_fork && Bt.size > 0 && !Vt && Gt();
	}
	return t;
}
function Gt() {
	Vt = !1;
	for (let e of Bt) {
		e.f & 1024 && k(e, S);
		let t;
		try {
			t = Kn(e);
		} catch {
			t = !0;
		}
		t && Qn(e);
	}
	Bt.clear();
}
function Kt(e) {
	P(e, e.v + 1);
}
function qt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Ye(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (i || s !== W) {
			var l = (c & x) === 0;
			if (l && k(s, t), c & 131072) Bt.add(s);
			else if (c & 2) {
				var u = s;
				j?.delete(u), c & 65536 || (c & 512 && (W === null || !(W.f & 2097152)) && (s.f |= se), qt(u, S, n));
			} else if (l) {
				var d = s;
				c & 16 && Ft !== null && Ft.add(d), n === null ? Lt(d) : n.push(d);
			}
		}
	}
}
function Jt(e) {
	if (typeof e != "object" || !e || de in e || fe in e) return e;
	let t = h(e);
	if (t !== p && t !== m) return e;
	var n = /* @__PURE__ */ new Map(), i = a(e), o = /* @__PURE__ */ Ut(0), s = null, c = Un, l = (e) => {
		if (Un === c) return e();
		var t = V, n = Un;
		U(null), Wn(c);
		var r = e();
		return U(t), Wn(n), r;
	};
	return i && n.set("length", /* @__PURE__ */ Ut(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && Ve();
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
			if (i === de) return e;
			var o = n.get(i), c = i in t;
			if (o === void 0 && (!c || d(t, i)?.writable) && (o = l(() => /* @__PURE__ */ Ut(Jt(c ? t[i] : r), s)), n.set(i, o)), o !== void 0) {
				var u = X(o);
				return u === r ? void 0 : u;
			}
			return Reflect.get(t, i, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var i = Reflect.getOwnPropertyDescriptor(e, t);
			if (i && "value" in i) {
				var a = n.get(t);
				a && (i.value = X(a));
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
			if (t === de) return !0;
			var i = n.get(t), a = i !== void 0 && i.v !== r || Reflect.has(e, t);
			return (i !== void 0 || W !== null && (!a || d(e, t)?.writable)) && (i === void 0 && (i = l(() => /* @__PURE__ */ Ut(a ? Jt(e[t]) : r, s)), n.set(t, i)), X(i) === r) ? !1 : a;
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
			var ee = Reflect.getOwnPropertyDescriptor(e, t);
			if (ee?.set && ee.set.call(c, a), !f) {
				if (i && typeof t == "string") {
					var g = n.get("length"), _ = Number(t);
					Number.isInteger(_) && _ >= g.v && P(g, _ + 1);
				}
				Kt(o);
			}
			return !0;
		},
		ownKeys(e) {
			X(o);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== r;
			});
			for (var [i, a] of n) a.v !== r && !(i in e) && t.push(i);
			return t;
		},
		setPrototypeOf() {
			He();
		}
	});
}
var Yt, Xt, Zt, Qt;
function $t() {
	if (Yt === void 0) {
		Yt = window, Xt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Zt = d(t, "firstChild").get, Qt = d(t, "nextSibling").get, ee(e) && (e[ge] = void 0, e[he] = null, e[_e] = void 0, e.__e = void 0), ee(n) && (n[ve] = void 0);
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
	if (!w) return /* @__PURE__ */ tn(e);
	var n = /* @__PURE__ */ tn(T);
	if (n === null) n = T.appendChild(en());
	else if (t && n.nodeType !== 3) {
		var r = en();
		return n?.before(r), E(r), r;
	}
	return t && cn(n), E(n), n;
}
function nn(e, t = !1) {
	if (!w) {
		var n = /* @__PURE__ */ tn(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ F(n) : n;
	}
	if (t) {
		if (T?.nodeType !== 3) {
			var r = en();
			return T?.before(r), E(r), r;
		}
		cn(T);
	}
	return T;
}
function rn(e, t = !1) {
	if (!w) return /* @__PURE__ */ tn(e);
	var n = I(e, t);
	return D(e), n;
}
function L(e, t = 1, n = !1) {
	let r = w ? T : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ F(r);
	if (!w) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = en();
			return r === null ? i?.after(a) : r.before(a), E(a), a;
		}
		cn(r);
	}
	return E(r), r;
}
function an(e) {
	e.textContent = "";
}
function on() {
	return !1;
}
function sn(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function cn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
function ln(e) {
	var t = W;
	if (t === null) return V.f |= ue, e;
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
function un(e) {
	W === null && (V === null && Le(e), Ie()), Ln && Fe(e);
}
function dn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function z(e, t) {
	var n = W;
	n !== null && n.f & 8192 && (e |= te);
	var r = {
		ctx: O,
		deps: null,
		nodes: null,
		f: e | x | 512,
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
	A?.register_created_effect(r);
	var i = r;
	if (e & 4) Ot === null ? Mt.ensure().schedule(r) : Ot.push(r);
	else if (t !== null) {
		try {
			Qn(r);
		} catch (e) {
			throw B(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= ie));
	}
	if (i !== null && (i.parent = n, n !== null && dn(i, n), V !== null && V.f & 2 && !(e & 64))) {
		var a = V;
		(a.effects ??= []).push(i);
	}
	return r;
}
function fn() {
	return V !== null && !H;
}
function pn(e) {
	let t = z(8, null);
	return k(t, b), t.teardown = e, t;
}
function mn(e) {
	un("$effect");
	var t = W.f;
	if (!V && t & 32 && O !== null && !O.i) {
		var n = O;
		(n.e ??= []).push(e);
	} else return hn(e);
}
function hn(e) {
	return z(4 | oe, e);
}
function gn(e) {
	return un("$effect.pre"), z(8 | oe, e);
}
function _n(e) {
	Mt.ensure();
	let t = z(64 | ae, e);
	return () => {
		B(t);
	};
}
function vn(e) {
	Mt.ensure();
	let t = z(64 | ae, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? An(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function yn(e) {
	return z(4, e);
}
function bn(e) {
	return z(le | ae, e);
}
function xn(e, t = 0) {
	return z(8 | t, e);
}
function Sn(e, t = [], n = [], r = []) {
	ut(r, t, n, (t) => {
		z(8, () => {
			e(...t.map(X));
		});
	});
}
function Cn(e, t = 0) {
	return z(16 | t, e);
}
function wn(e) {
	return z(32 | ae, e);
}
function Tn(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = Ln, r = V;
		Rn(!0), U(null);
		try {
			t.call(null);
		} catch (t) {
			R(t, e.parent);
		} finally {
			Rn(n), U(r);
		}
	}
}
function En(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && ct(() => {
			e.abort(be);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function Dn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (On(e.nodes.start, e.nodes.end), n = !0), e.f |= re, En(e, t && !n), Zn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Tn(e), e.f ^= re, e.f |= C;
	var i = e.parent;
	i !== null && i.first !== null && kn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function On(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ F(e);
		e.remove(), e = n;
	}
}
function kn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function An(e, t, n = !0) {
	var r = [];
	e.f |= 256, jn(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function jn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= te;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = !!(i.f & 65536) || !!(i.f & 32) && !!(e.f & 16);
				jn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Mn(e) {
	e.f &= -257, Nn(e, !0);
}
function Nn(e, t) {
	if (!(e.f & 256) && e.f & 8192) {
		e.f ^= te, e.f & 1024 || (k(e, x), Mt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = !!(n.f & 65536) || !!(n.f & 32);
			Nn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Pn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ F(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Fn = null, In = !1, Ln = !1;
function Rn(e) {
	Ln = e;
}
var V = null, H = !1;
function U(e) {
	V = e;
}
var W = null;
function G(e) {
	W = e;
}
var K = null;
function zn(e) {
	V !== null && (K ??= /* @__PURE__ */ new Set()).add(e);
}
var q = null, J = 0, Y = null;
function Bn(e) {
	Y = e;
}
var Vn = 1, Hn = 0, Un = Hn;
function Wn(e) {
	Un = e;
}
function Gn() {
	return ++Vn;
}
function Kn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~se), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Kn(a) && bt(a), a.wv > e.wv) return !0;
		}
		t & 512 && j === null && k(e, b);
	}
	return !1;
}
function qn(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(K !== null && K.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? qn(a, t, !1) : t === a && (n ? k(a, x) : a.f & 1024 && k(a, S), Lt(a));
	}
}
function Jn(e) {
	var t = q, n = J, r = Y, i = V, a = K, o = O, s = H, c = Un, l = e.f;
	q = null, J = 0, Y = null, V = l & 96 ? null : e, K = null, Ge(e.ctx), H = !1, Un = ++Hn, e.ac !== null && (ct(() => {
		e.ac.abort(be);
	}), e.ac = null);
	try {
		e.f |= ce;
		var u = e.fn, d = u();
		e.f |= ne;
		var f = Yn(e);
		if (Ye() && Y !== null && !H && f !== null && !(e.f & 6146)) for (var p = 0; p < Y.length; p++) qn(Y[p], e);
		if (i !== null && i !== e) {
			if (Hn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Hn;
			if (t !== null) for (let e of t) e.rv = Hn;
			Y !== null && (r === null ? r = Y : r.push(...Y));
		}
		return e.f & 8388608 && (e.f ^= ue), d;
	} catch (t) {
		return Yn(e), ln(t);
	} finally {
		e.f ^= ce, q = t, J = n, Y = r, V = i, K = a, Ge(o), H = s, Un = c;
	}
}
function Yn(e) {
	var t = e.deps, n = A?.is_fork;
	if (q !== null) {
		var r;
		if (n || Zn(e, J), t !== null && J > 0) for (t.length = J + q.length, r = 0; r < q.length; r++) t[J + r] = q[r];
		else e.deps = t = q;
		if (fn() && e.f & 512) for (r = J; r < t.length; r++) (t[r].reactions ??= []).push(e);
	} else !n && t !== null && J < t.length && (Zn(e, J), t.length = J);
	return t;
}
function Xn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var i = o.call(n, e);
		if (i !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[i] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (q === null || !s.call(q, t))) {
		var c = t;
		c.f & 512 && (c.f ^= 512, c.f &= ~se), c.v !== r && tt(c), c.ac !== null && ct(() => {
			c.ac.abort(be), c.ac = null, k(c, x);
		}), xt(c), Zn(c, 0);
	}
}
function Zn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Xn(e, n[r]);
}
function Qn(e) {
	var t = e.f;
	if (!(t & 16384)) {
		k(e, b);
		var n = W, r = In;
		W = e, In = !(t & 96);
		try {
			t & 16777232 ? Dn(e) : En(e), Tn(e);
			var i = Jn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Vn;
		} finally {
			In = r, W = n;
		}
	}
}
async function $n() {
	await Promise.resolve(), Nt();
}
function X(e) {
	var t = !!(e.f & 2);
	if (Fn?.add(e), V !== null && !H && !(W !== null && W.f & 16384) && (K === null || !K.has(e))) {
		var n = V.deps;
		if (V.f & 2097152) e.rv < Hn && (e.rv = Hn, q === null && n !== null && n[J] === e ? J++ : q === null ? q = [e] : q.push(e));
		else {
			V.deps ??= [], s.call(V.deps, e) || V.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [V] : s.call(r, V) || r.push(V);
		}
	}
	if (Ln && M.has(e)) return M.get(e);
	if (t) {
		var i = e;
		if (Ln) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || tr(i)) && (a = yt(i)), M.set(i, a), a;
		}
		var o = !(i.f & 512) && !H && V !== null && (In || !!(V.f & 512)), c = (i.f & ne) === 0;
		Kn(i) && (o && (i.f |= 512), bt(i)), o && !c && (St(i), er(i));
	}
	if (j?.has(e)) return j.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function er(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (St(t), er(t));
}
function tr(e) {
	if (e.v === r) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (M.has(t) || t.f & 2 && tr(t)) return !0;
	return !1;
}
function nr(e) {
	var t = H;
	try {
		return H = !0, e();
	} finally {
		H = t;
	}
}
function rr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (de in e) ir(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && de in n && ir(n);
		}
	}
}
function ir(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			ir(e[n], t);
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
var ar = Symbol("events"), or = /* @__PURE__ */ new Set(), sr = /* @__PURE__ */ new Set();
function cr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || fr.call(t, e), !e.cancelBubble) return ct(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? Qe(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function lr(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = cr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && pn(() => {
		t.removeEventListener(e, o, a);
	});
}
var ur = null, dr = !1;
function fr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	ur = e, dr || (dr = !0, setTimeout(() => {
		dr = !1, ur = null;
	}));
	var o = 0, s = ur === e && e[ar];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[ar] = t;
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
		var d = V, f = W;
		U(null), G(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[ar]?.[r];
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
			e[ar] = t, delete e.currentTarget, U(d), G(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var pr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function mr(e) {
	return pr?.createHTML(e) ?? e;
}
function hr(e) {
	var t = sn("template");
	return t.innerHTML = mr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function gr(e, t) {
	var n = W;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Z(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (w) return gr(T, null), T;
		i === void 0 && (i = hr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ tn(i)));
		var t = r || Xt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ tn(t), s = t.lastChild;
			gr(o, s);
		} else gr(t, t);
		return t;
	};
}
function Q(e, t) {
	if (w) {
		var n = W;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = T), Ee();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var _r = ["touchstart", "touchmove"];
function vr(e) {
	return _r.includes(e);
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function yr(e) {
	let t = 0, n = Ht(0), r;
	return () => {
		fn() && (X(n), xn(() => (t === 0 && (r = nr(() => e(() => Kt(n)))), t += 1, () => {
			Qe(() => {
				--t, t === 0 && (r?.(), r = void 0, Kt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var br = ie | ae;
function xr(e, t, n, r) {
	new Sr(e, t, n, r);
}
var Sr = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = w ? T : null;
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
	#h = yr(() => (this.#m = Ht(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = W;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = W.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Cn(() => {
			if (w) {
				let e = this.#t;
				Ee();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#y() : this.#g();
			} else this.#b();
		}, br), w && (this.#e = T);
	}
	#g() {
		try {
			this.#a = wn(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#v(e);
		Qe(r), t && (this.#s = wn(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#v(e) {
		var t = !1, n = !1;
		let r = () => {
			if (t) {
				we();
				return;
			}
			t = !0, n && We(), this.#s !== null && An(this.#s, () => {
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
		e && (this.is_pending = !0, this.#o = wn(() => e(this.#e)), Qe(() => {
			var e = this.#c = document.createDocumentFragment(), t = en(), n = !1;
			if (e.append(t), this.#a = this.#S(() => {
				try {
					return wn(() => this.#r(t));
				} catch (e) {
					try {
						this.error(e), n = !0;
					} catch (e) {
						R(e, this.#i.parent);
					}
					return null;
				}
			}), this.#a === null) {
				this.#c = null, n && this.#x(A);
				return;
			}
			this.#u === 0 && (this.#e.before(e), this.#c = null, An(this.#o, () => {
				this.#o = null;
			}), this.#x(A));
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = wn(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Pn(this.#a, e);
				let t = this.#n.pending;
				this.#o = wn(() => t(this.#e));
			} else this.#x(A);
		} catch (e) {
			this.error(e);
		}
	}
	#x(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		rt(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#S(e) {
		var t = W, n = V, r = O;
		G(this.#i), U(this.#i), Ge(this.#i.ctx);
		try {
			return Mt.ensure(), e();
		} finally {
			G(t), U(n), Ge(r);
		}
	}
	#C(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#C(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#x(t), this.#o && An(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#C(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, Qe(() => {
			this.#d = !1, this.#m && Wt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), X(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		A?.is_fork ? (this.#a && A.skip_effect(this.#a), this.#o && A.skip_effect(this.#o), this.#s && A.skip_effect(this.#s), A.oncommit(() => {
			this.#w(e);
		})) : this.#w(e);
	}
	#w(e) {
		this.#a &&= (B(this.#a), null), this.#o &&= (B(this.#o), null), this.#s &&= (B(this.#s), null), w && (E(this.#t), De(), E(Oe()));
		let t = this.#n.failed, n = (e) => {
			let { reset: n, invoke_onerror: r } = this.#v(e);
			r(), t && (this.#s = this.#S(() => {
				try {
					return wn(() => {
						var r = W;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return R(e, this.#i.parent), null;
				}
			}));
		};
		Qe(() => {
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
function $(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[ve] ??= e.nodeValue) && (e[ve] = n, e.nodeValue = `${n}`);
}
function Cr(e, t) {
	return Er(e, t);
}
function wr(e, t) {
	$t(), t.intro = t.intro ?? !1;
	let r = t.target, i = w, a = T;
	try {
		for (var o = /* @__PURE__ */ tn(r); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ F(o);
		if (!o) throw n;
		Te(!0), E(o);
		let i = Er(e, {
			...t,
			anchor: o
		});
		return Te(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== n && console.warn("Failed to hydrate: ", i), t.recover === !1 && ze(), $t(), an(r), Te(!1), Cr(e, t);
	} finally {
		Te(i), E(a);
	}
}
var Tr = /* @__PURE__ */ new Map();
function Er(e, { target: t, anchor: r, props: i = {}, events: a, context: o, intro: s = !0, transformError: l }) {
	$t();
	var u = void 0, d = vn(() => {
		var s = r ?? t.appendChild(en());
		xr(s, { pending: () => {} }, (t) => {
			Ke({});
			var r = O;
			if (o && (r.c = o), a && (i.$$events = a), w && gr(t, null), u = e(t, i) || Je(), w && (W.nodes.end = T, T === null || T.nodeType !== 8 || T.data !== "]")) throw Ce(), n;
			qe();
		}, l);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = vr(r);
					for (let e of [t, document]) {
						var a = Tr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), Tr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, fr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(c(or)), sr.add(f), () => {
			for (var e of d) for (let r of [t, document]) {
				var n = Tr.get(r), i = n.get(e);
				--i == 0 ? (r.removeEventListener(e, fr), n.delete(e), n.size === 0 && Tr.delete(r)) : n.set(e, i);
			}
			sr.delete(f), s !== r && s.parentNode?.removeChild(s);
		};
	});
	return Dr.set(u, d), u;
}
var Dr = /* @__PURE__ */ new WeakMap();
function Or(e, t) {
	let n = Dr.get(e);
	return n ? (Dr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var kr = class {
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
			if (n) Mn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (Mn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (B(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Pn(r, t), t.append(en()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), An(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = A, r = on();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = document.createDocumentFragment(), a = en();
				i.append(a), this.#n.set(e, {
					effect: wn(() => t(a)),
					fragment: i
				});
			} else this.#t.set(e, wn(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else w && (this.anchor = T), this.#a(n);
	}
};
function Ar(t) {
	O === null && Ne("onMount"), e && O.l !== null ? jr(O).m.push(t) : mn(() => {
		let e = nr(t);
		if (typeof e == "function") return e;
	});
}
function jr(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Mr(e, t, n = !1) {
	var r;
	w && (r = T, Ee());
	var i = new kr(e), a = n ? ie : 0;
	function o(e, t) {
		if (w) {
			var n = ke(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Oe();
				E(a), i.anchor = a, Te(!1), i.ensure(e, t), Te(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	Cn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Nr(e, t) {
	yn(() => {
		e = W?.parent?.nodes?.start ?? e;
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = sn("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/shared/attributes.js
var Pr = [..." 	\n\r\f\xA0\v﻿"];
function Fr(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Pr.includes(r[o - 1])) && (s === r.length || Pr.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/class.js
function Ir(e, t, n, r, i, a) {
	var o = e[ge];
	if (w || o !== n || o === void 0) {
		var s = Fr(n, r, a);
		(!w || s !== e.getAttribute("class")) && (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e[ge] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Lr = Symbol("is custom element"), Rr = Symbol("is html"), zr = xe ? "link" : "LINK", Br = xe ? "progress" : "PROGRESS";
function Vr(e) {
	if (w) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Ur(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Ur(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ye] = n, Qe(n), st();
	}
}
function Hr(e, t) {
	var n = Wr(e);
	n.value !== (n.value = t ?? void 0) && (e.value !== t || t === 0 && e.nodeName === Br) && (e.value = t ?? "");
}
function Ur(e, t, n, r) {
	var i = Wr(e);
	w && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === zr) || i[t] !== (i[t] = n) && (t === "loading" && (e[me] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Kr(e).has(t) ? e[t] = n : e.setAttribute(t, n));
}
function Wr(e) {
	return e[he] ??= {
		[Lr]: e.nodeName.includes("-"),
		[Rr]: e.namespaceURI === i
	};
}
var Gr = /* @__PURE__ */ new Map();
function Kr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Gr.get(t);
	if (n) return n;
	Gr.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = f(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.add(o);
		i = h(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function qr(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	lt(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = Jr(e) ? Yr(a) : a, n(a), A !== null && r.add(A), await $n(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (w && e.defaultValue !== e.value || nr(t) == null && e.value) && (n(Jr(e) ? Yr(e.value) : e.value), A !== null && r.add(A)), xn(() => {
		var n = t();
		if (e === document.activeElement) {
			var i = A;
			if (r.has(i)) return;
		}
		Jr(e) && n === Yr(e.value) || (e.type !== "date" || n || e.value) && n !== e.value && (e.value = n ?? "");
	});
}
function Jr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Yr(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Xr(e = !1) {
	let t = O, n = t.l.u;
	if (!n) return;
	let r = () => rr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ mt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => X(i);
	}
	n.b.length && gn(() => {
		Zr(t, r), v(n.b);
	}), mn(() => {
		let e = nr(() => n.m.map(_));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && mn(() => {
		Zr(t, r), v(n.a);
	});
}
function Zr(e, t) {
	if (e.l.s) for (let t of e.l.s) X(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function Qr(t, n, r, i) {
	var a = !e || !!(r & 2), o = !!(r & 8), s = !!(r & 16), c = i, l = !0, u = void 0, f = () => s && a ? (u ??= /* @__PURE__ */ mt(i), X(u)) : (l && (l = !1, c = s ? nr(i) : i), c);
	let p;
	if (o) {
		var m = de in t || pe in t;
		p = d(t, n)?.set ?? (m && n in t ? (e) => t[n] = e : void 0);
	}
	var h, ee = !1;
	o ? [h, ee] = at(() => t[n]) : h = t[n], h === void 0 && i !== void 0 && (h = f(), p && (a && Be(n), p(h)));
	var g = a ? () => {
		var e = t[n];
		return e === void 0 ? f() : (l = !0, e);
	} : () => {
		var e = t[n];
		return e !== void 0 && (c = void 0), e === void 0 ? c : e;
	};
	if (a && !(r & 4)) return g;
	if (p) {
		var _ = t.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || _ || ee) && p(t ? g() : e), e) : g();
		});
	}
	var v = !1, y = (r & 1 ? mt : _t)(() => (v = !1, g()));
	o && X(y);
	var b = W;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? X(y) : a && o ? Jt(e) : e;
			return P(y, n), v = !0, c !== void 0 && (c = n), e;
		}
		return Ln && v || b.f & 16384 ? y.v : X(y);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function $r(e) {
	return new ei(e);
}
var ei = class {
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
				return X(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === pe || (X(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return P(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		});
		this.#t = (e.hydrate ? wr : Cr)(e.component, {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		}), (!e?.props?.$$host || e.sync === !1) && Nt(), this.#e = r.$$events;
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
			Or(this.#t);
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
}, ti;
typeof HTMLElement == "function" && (ti = class extends HTMLElement {
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
					let n = sn("slot");
					e !== "default" && (n.name = e), Q(t, n);
				};
			}
			let t = {}, n = ri(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = ni(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = $r({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = _n(() => {
				xn(() => {
					this.$$r = !0;
					for (let e of l(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = ni(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = ni(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
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
function ni(e, t, n, r) {
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
function ri(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function ii(e, t, n, r, i, a) {
	let o = class extends ti {
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
				n = ni(e, n, t), this.$$d[e] = n;
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
//#region SlskdCard.svelte
var ai = /* @__PURE__ */ Z("<span class=\"status-badge success svelte-11uhbwz\">● Connected</span>"), oi = /* @__PURE__ */ Z("<span class=\"status-badge warning svelte-11uhbwz\">⚠ Disconnected</span>"), si = /* @__PURE__ */ Z("<span class=\"status-badge active svelte-11uhbwz\">● Active</span>"), ci = /* @__PURE__ */ Z("<button class=\"btn-ghost small svelte-11uhbwz\">Activate</button>"), li = /* @__PURE__ */ Z("<div class=\"loading-state svelte-11uhbwz\">Loading...</div>"), ui = /* @__PURE__ */ Z("<button class=\"btn-ghost svelte-11uhbwz\"> </button>"), di = /* @__PURE__ */ Z("<div> </div>"), fi = /* @__PURE__ */ Z("<div class=\"webhook-details\"><label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Webhook Callback URL</span> <div class=\"copy-input-wrapper svelte-11uhbwz\"><input type=\"text\" readonly=\"\" class=\"input-field readonly svelte-11uhbwz\"/> <button type=\"button\" class=\"btn-copy svelte-11uhbwz\"> </button></div> <span class=\"helper-text svelte-11uhbwz\">Add this URL to your slskd configuration to enable real-time\n              ingestion.</span></label> <div class=\"yaml-block svelte-11uhbwz\"><div class=\"yaml-header svelte-11uhbwz\"><span>slskd.yml Integration Config</span> <button type=\"button\" class=\"btn-ghost small svelte-11uhbwz\"> </button></div> <pre class=\"code-block svelte-11uhbwz\"><code> </code></pre></div> <div class=\"actions-row svelte-11uhbwz\"><button class=\"btn-ghost svelte-11uhbwz\"> </button> <button class=\"btn-ghost svelte-11uhbwz\">Refresh Details</button></div> <!></div>"), pi = /* @__PURE__ */ Z("<div class=\"loading-state svelte-11uhbwz\">Loading webhook configuration...</div>"), mi = /* @__PURE__ */ Z("<div class=\"settings-section svelte-11uhbwz\"><h3 class=\"section-title svelte-11uhbwz\">Server Configuration</h3> <div class=\"form-grid svelte-11uhbwz\"><label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Server URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:5030\" class=\"input-field svelte-11uhbwz\"/> <span class=\"helper-text svelte-11uhbwz\">Enter your slskd server address (include port, default :5030)</span></label> <label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Server Name (Optional)</span> <input type=\"text\" placeholder=\"My slskd Server\" class=\"input-field svelte-11uhbwz\"/></label> <label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">API Key</span> <div class=\"password-wrapper svelte-11uhbwz\"><input placeholder=\"Enter API key\" class=\"input-field svelte-11uhbwz\"/> <button type=\"button\" class=\"toggle-visibility svelte-11uhbwz\"> </button></div> <span class=\"helper-text svelte-11uhbwz\">API key from slskd settings (Options → Security → API Keys)</span></label> <div class=\"actions-row svelte-11uhbwz\"><button class=\"btn-primary svelte-11uhbwz\"> </button> <!></div></div></div> <div class=\"settings-section webhook-section svelte-11uhbwz\"><h3 class=\"section-title svelte-11uhbwz\">Webhooks & Automation</h3> <p class=\"section-description svelte-11uhbwz\">Configure slskd to immediately notify EchoSync upon download completion\n        or failure. This enables real-time tag verification, automatic library\n        admission, and immediate daemon transfer eviction.</p> <!></div>", 1), hi = /* @__PURE__ */ Z("<section class=\"plugin-card svelte-11uhbwz\"><div class=\"card-header svelte-11uhbwz\"><div class=\"header-left svelte-11uhbwz\"><h2 class=\"card-title svelte-11uhbwz\">Slskd</h2> <div class=\"badges svelte-11uhbwz\"><span class=\"type-badge svelte-11uhbwz\">Download Client</span> <!> <!></div></div> <div class=\"header-right svelte-11uhbwz\"><!> <button class=\"btn-ghost svelte-11uhbwz\"> </button></div></div> <!></section>"), gi = {
	hash: "svelte-11uhbwz",
	code: ".plugin-card.svelte-11uhbwz {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-11uhbwz {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle, #1e293b);}.header-left.svelte-11uhbwz {display:flex;align-items:center;gap:16px;}.card-title.svelte-11uhbwz {margin:0;font-size:20px;font-weight:700;}.badges.svelte-11uhbwz {display:flex;gap:8px;}.type-badge.svelte-11uhbwz {font-size:10px;padding:2px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);border-radius:4px;font-weight:700;text-transform:uppercase;}.status-badge.svelte-11uhbwz {font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-11uhbwz {background:rgba(16, 185, 129, 0.15);color:#10b981;}.status-badge.warning.svelte-11uhbwz {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-11uhbwz {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.header-right.svelte-11uhbwz {display:flex;gap:8px;}.btn-ghost.svelte-11uhbwz {padding:8px 16px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.small.svelte-11uhbwz {padding:4px 12px;font-size:11px;font-weight:700;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;}.btn-ghost.svelte-11uhbwz:hover {background:var(--bg-surface-elevated);filter:brightness(1.2);}.btn-primary.svelte-11uhbwz {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-11uhbwz:hover {opacity:0.9;}.loading-state.svelte-11uhbwz {padding:24px;text-align:center;color:var(--text-secondary, #94a3b8);}.settings-section.svelte-11uhbwz {margin-top:16px;}.section-title.svelte-11uhbwz {margin:0 0 16px 0;font-size:16px;font-weight:600;}.form-grid.svelte-11uhbwz {display:flex;flex-direction:column;gap:16px;}.form-field.svelte-11uhbwz {display:flex;flex-direction:column;gap:6px;}.field-label.svelte-11uhbwz {font-size:13px;color:var(--text-secondary, #94a3b8);}.input-field.svelte-11uhbwz {width:100%;padding:10px 14px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);border-radius:8px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.2s;}.input-field.svelte-11uhbwz:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.password-wrapper.svelte-11uhbwz {position:relative;display:flex;align-items:center;}.toggle-visibility.svelte-11uhbwz {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary, #f8fafc);}.helper-text.svelte-11uhbwz {font-size:11px;color:var(--text-secondary, #94a3b8);}.actions-row.svelte-11uhbwz {display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;}.webhook-section.svelte-11uhbwz {border-top:1px solid var(--border-subtle, #1e293b);padding-top:20px;margin-top:24px;}.section-description.svelte-11uhbwz {font-size:13px;color:var(--text-secondary, #94a3b8);margin:-8px 0 16px 0;line-height:1.4;}.copy-input-wrapper.svelte-11uhbwz {display:flex;gap:8px;}.input-field.readonly.svelte-11uhbwz {background:rgba(15, 23, 42, 0.6);color:var(--color-primary, #14b8a6);font-family:monospace;font-size:12px;}.btn-copy.svelte-11uhbwz {padding:0 16px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:12px;cursor:pointer;font-weight:600;transition:all 0.2s;white-space:nowrap;}.btn-copy.svelte-11uhbwz:hover {background:var(--color-primary, #14b8a6);color:#000;}.yaml-block.svelte-11uhbwz {margin-top:12px;background:#090d16;border:1px solid var(--border-subtle, #1e293b);border-radius:8px;overflow:hidden;}.yaml-header.svelte-11uhbwz {display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:rgba(30, 41, 59, 0.4);border-bottom:1px solid var(--border-subtle, #1e293b);font-size:12px;font-weight:600;color:var(--text-secondary, #94a3b8);}.code-block.svelte-11uhbwz {margin:0;padding:12px;font-family:\"JetBrains Mono\", \"Fira Code\", monospace;font-size:12px;color:#38bdf8;overflow-x:auto;white-space:pre;line-height:1.4;}.test-result-banner.svelte-11uhbwz {margin-top:12px;padding:10px 14px;border-radius:8px;font-size:13px;font-weight:500;}.test-result-banner.success.svelte-11uhbwz {background:rgba(16, 185, 129, 0.15);color:#10b981;border:1px solid rgba(16, 185, 129, 0.3);}.test-result-banner.error.svelte-11uhbwz {background:rgba(239, 68, 68, 0.15);color:#ef4444;border:1px solid rgba(239, 68, 68, 0.3);}"
};
function _i(e, t) {
	Ke(t, !1), Nr(e, gi);
	let n = Qr(t, "apiBase", 12, ""), r = /* @__PURE__ */ N(""), i = /* @__PURE__ */ N(""), a = /* @__PURE__ */ N(""), o = /* @__PURE__ */ N(!1), s = /* @__PURE__ */ N(!0), c = /* @__PURE__ */ N(!1), l = /* @__PURE__ */ N(!1), u = /* @__PURE__ */ N(!1), d = /* @__PURE__ */ N(!1), f = /* @__PURE__ */ N(!1), p = !1, m = /* @__PURE__ */ N(!1), h = /* @__PURE__ */ N(null), ee = /* @__PURE__ */ N(!1), g = /* @__PURE__ */ N(!1), _ = /* @__PURE__ */ N(null), v = /* @__PURE__ */ N(!1), y = /* @__PURE__ */ N(!1);
	Ar(async () => {
		await C(), await S(), await b(), P(s, !1);
	});
	async function b() {
		try {
			P(ee, !0);
			let e = await (await fetch(`${n()}/webhooks/info`)).json();
			e && e.endpoint && P(h, e.endpoint);
		} catch (e) {
			console.error("Failed to load webhook info:", e);
		} finally {
			P(ee, !1);
		}
	}
	async function x() {
		try {
			P(g, !0), P(_, null);
			let e = await fetch(`${n()}/webhooks/test`, { method: "POST" }), t = await e.json();
			e.ok && t.success ? P(_, {
				success: !0,
				message: "Ping successful! Webhook gateway received and dispatched event."
			}) : P(_, {
				success: !1,
				message: t.detail || "Ping failed."
			});
		} catch (e) {
			P(_, {
				success: !1,
				message: `Ping failed: ${e.message}`
			});
		} finally {
			P(g, !1);
		}
	}
	async function S() {
		try {
			let e = await (await fetch(`${n()}/download-clients/active`)).json();
			P(m, e.active_client === "slskd");
		} catch (e) {
			console.error("Failed to check active status:", e);
		}
	}
	async function te() {
		try {
			await fetch(`${n()}/download-clients/activate`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ client: "slskd" })
			}), P(m, !0);
		} catch (e) {
			console.error("Failed to activate client:", e);
		}
	}
	async function C() {
		try {
			let e = await (await fetch(`${n()}/settings`)).json();
			e && (P(r, e.slskd_url || ""), P(a, e.server_name || ""), P(i, e.api_key || ""), P(f, e.has_api_key || !1), P(o, e.configured || !1));
		} catch (e) {
			console.error("Failed to load slskd settings:", e);
		}
	}
	async function ne() {
		if (!X(r).trim()) {
			console.error("Server URL is required");
			return;
		}
		try {
			P(c, !0);
			let e = {
				slskd_url: X(r),
				server_name: X(a)
			};
			X(i) && X(i) !== "****" && (e.api_key = X(i)), await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), await C();
		} catch (e) {
			console.error("Failed to save slskd settings:", e);
		} finally {
			P(c, !1);
		}
	}
	async function re() {
		if (X(r).trim()) try {
			P(l, !0), (await (await fetch(`${n()}/connection/test`, { method: "POST" })).json())?.success ? (P(o, !0), await C()) : P(o, !1);
		} catch (e) {
			console.error("Failed to test slskd connection:", e), P(o, !1);
		} finally {
			P(l, !1);
		}
	}
	async function ie() {
		let e = !X(d);
		if (P(d, e), e && X(f) && X(i) === "****" && !p) try {
			let e = await (await fetch(`${n()}/settings/key`)).json();
			e && e.api_key ? (P(i, e.api_key), p = !0) : P(d, !1);
		} catch {
			P(d, !1);
		}
		!e && p && (P(i, "****"), p = !1);
	}
	function ae(e, t) {
		navigator?.clipboard && navigator.clipboard.writeText(e).then(() => {
			t === "yaml" ? (P(v, !0), setTimeout(() => P(v, !1), 2e3)) : (P(y, !0), setTimeout(() => P(y, !1), 2e3));
		});
	}
	var oe = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Nt();
		}
	};
	Xr();
	var se = hi(), ce = I(se), le = I(ce), ue = L(I(le), 2), de = L(I(ue), 2), fe = (e) => {
		Q(e, ai());
	}, pe = (e) => {
		Q(e, oi());
	};
	Mr(de, (e) => {
		X(o) ? e(fe) : X(r) && e(pe, 1);
	});
	var me = L(de, 2), he = (e) => {
		Q(e, si());
	};
	Mr(me, (e) => {
		X(m) && e(he);
	}), D(ue), D(le);
	var ge = L(le, 2), _e = I(ge), ve = (e) => {
		var t = ci();
		lr("click", t, te), Q(e, t);
	};
	Mr(_e, (e) => {
		!X(m) && X(o) && e(ve);
	});
	var ye = L(_e, 2), be = rn(ye, !0);
	D(ge), D(ce);
	var xe = L(ce, 2), Se = (e) => {
		Q(e, li());
	}, Ce = (e) => {
		var t = mi(), n = nn(t), o = L(I(n), 2), s = I(o), u = L(I(s), 2);
		Vr(u), De(2), D(s);
		var p = L(s, 2), m = L(I(p), 2);
		Vr(m), D(p);
		var S = L(p, 2), te = L(I(S), 2), C = I(te);
		Vr(C);
		var oe = L(C, 2), se = rn(oe, !0);
		D(te), De(2), D(S);
		var ce = L(S, 2), le = I(ce), ue = rn(le, !0), de = L(le, 2), fe = (e) => {
			var t = ui(), n = rn(t, !0);
			Sn(() => {
				t.disabled = X(l), $(n, X(l) ? "Testing..." : "Test Connection");
			}), lr("click", t, re), Q(e, t);
		};
		Mr(de, (e) => {
			X(r) && (X(f) || X(i)) && e(fe);
		}), D(ce), D(o), D(n);
		var pe = L(n, 2), me = L(I(pe), 4), he = (e) => {
			var t = fi(), n = I(t), r = L(I(n), 2), i = I(r);
			Vr(i);
			var a = L(i, 2), o = rn(a, !0);
			D(r), De(2), D(n);
			var s = L(n, 2), c = I(s), l = L(I(c), 2), u = rn(l, !0);
			D(c);
			var d = L(c, 2), f = rn(I(d), !0);
			D(d), D(s);
			var p = L(s, 2), m = I(p), S = rn(m, !0), te = L(m, 2);
			D(p);
			var C = L(p, 2), ne = (e) => {
				var t = di(), n = rn(t, !0);
				Sn(() => {
					Ir(t, 1, `test-result-banner ${X(_), nr(() => X(_).success ? "success" : "error") ?? ""}`, "svelte-11uhbwz"), $(n, (X(_), nr(() => X(_).message)));
				}), Q(e, t);
			};
			Mr(C, (e) => {
				X(_) && e(ne);
			}), D(t), Sn(() => {
				Hr(i, (X(h), nr(() => `${X(h).url}${X(h).secret ? "?secret=" + X(h).secret : ""}`))), $(o, X(y) ? "Copied!" : "Copy"), $(u, X(v) ? "Copied!" : "Copy YAML"), $(f, (X(h), nr(() => X(h).yaml_template))), m.disabled = X(g), $(S, X(g) ? "Pinging Webhook..." : "Test Webhook Ingress"), te.disabled = X(ee);
			}), lr("click", a, () => ae(`${X(h).url}${X(h).secret ? "?secret=" + X(h).secret : ""}`, "url")), lr("click", l, () => ae(X(h).yaml_template, "yaml")), lr("click", m, x), lr("click", te, b), Q(e, t);
		}, ge = (e) => {
			Q(e, pi());
		};
		Mr(me, (e) => {
			X(h) ? e(he) : e(ge, -1);
		}), D(pe), Sn(() => {
			Ur(C, "type", X(d) ? "text" : "password"), $(se, X(d) ? "🙈" : "👁️"), le.disabled = X(c), $(ue, X(c) ? "Saving..." : "Save Settings");
		}), qr(u, () => X(r), (e) => P(r, e)), qr(m, () => X(a), (e) => P(a, e)), qr(C, () => X(i), (e) => P(i, e)), lr("click", oe, ie), lr("click", le, ne), Q(e, t);
	};
	return Mr(xe, (e) => {
		X(s) ? e(Se) : X(u) || e(Ce, 1);
	}), D(se), Sn(() => $(be, X(u) ? "Expand" : "Collapse")), lr("click", ye, () => P(u, !X(u))), Q(e, se), qe(oe);
}
customElements.define("slskd-dashboard-card", ii(_i, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { _i as default };

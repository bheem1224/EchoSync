// node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
// node_modules/svelte/src/internal/flags/index.js
var e = !1;
function t() {
	e = !0;
}
// node_modules/svelte/src/internal/flags/legacy.js
t();
// node_modules/svelte/src/constants.js
var n = {}, r = Symbol("uninitialized"), i = "http://www.w3.org/1999/xhtml", a = Array.isArray, o = Array.prototype.indexOf, s = Array.prototype.includes, c = Array.from, l = Object.keys, u = Object.defineProperty, d = Object.getOwnPropertyDescriptor, f = Object.getOwnPropertyDescriptors, p = Object.prototype, m = Array.prototype, h = Object.getPrototypeOf, ee = Object.isExtensible, g = () => {};
function te(e) {
	return e();
}
function _(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function ne() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var v = 1024, y = 2048, b = 4096, re = 8192, ie = 16384, ae = 32768, oe = 1 << 25, se = 65536, x = 1 << 19, ce = 1 << 20, le = 1 << 21, ue = 1 << 22, de = 1 << 23, fe = Symbol("$state"), pe = Symbol("component"), me = Symbol("legacy props"), he = Symbol(""), ge = Symbol("attributes"), _e = Symbol("class"), ve = Symbol("style"), ye = Symbol("text"), be = Symbol("form reset"), xe = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), Se = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function Ce() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function we(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Te() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
// node_modules/svelte/src/internal/client/dom/hydration.js
var S = !1;
function Ee(e) {
	S = e;
}
var C;
function w(e) {
	if (e === null) throw we(), n;
	return C = e;
}
function De() {
	return w(/* @__PURE__ */ en(C));
}
function T(e) {
	if (S) {
		if (/* @__PURE__ */ en(C) !== null) throw we(), n;
		C = e;
	}
}
function Oe(e = 1) {
	if (S) {
		for (var t = e, n = C; t--;) n = /* @__PURE__ */ en(n);
		C = n;
	}
}
function ke(e = !0) {
	for (var t = 0, n = C;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r.startsWith("[?") || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ en(n);
		e && n.remove(), n = i;
	}
}
function Ae(e) {
	if (!e || e.nodeType !== 8) throw we(), n;
	return e.data;
}
// node_modules/svelte/src/internal/client/reactivity/equality.js
function je(e) {
	return e === this.v;
}
function Me(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Ne(e) {
	return !Me(e, this.v);
}
function Pe(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
// node_modules/svelte/src/internal/client/errors.js
function Fe() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Ie(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Le() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Re(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function ze() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Be() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Ve(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function He() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Ue() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function We() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Ge() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
// node_modules/svelte/src/internal/client/context.js
var E = null;
function Ke(e) {
	E = e;
}
function qe(t, n = !1, r) {
	E = {
		p: E,
		i: !1,
		c: null,
		e: null,
		s: t,
		x: null,
		r: G,
		l: e && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Je(e) {
	var t = E, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) pn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, E = t.p, Ye(e);
}
function Ye(e = {}) {
	return u(e, pe, { value: !0 }), e;
}
function Xe() {
	return !e || E !== null && E.l === null;
}
// node_modules/svelte/src/internal/client/dom/task.js
var Ze = [];
function Qe() {
	var e = Ze;
	Ze = [], _(e);
}
function D(e) {
	if (Ze.length === 0 && !Ct) {
		var t = Ze;
		queueMicrotask(() => {
			t === Ze && Qe();
		});
	}
	Ze.push(e);
}
function $e() {
	for (; Ze.length > 0;) Qe();
}
// node_modules/svelte/src/internal/client/reactivity/status.js
var et = ~(y | b | v);
function O(e, t) {
	e.f = e.f & et | t;
}
function tt(e) {
	e.f & 512 || e.deps === null ? O(e, v) : O(e, b);
}
// node_modules/svelte/src/internal/client/reactivity/utils.js
function nt(e, t) {
	e.f & 2048 ? t.set(e, y) : e.f & 4096 && t.get(e) !== 2048 && t.set(e, b), O(e, v);
}
// node_modules/svelte/src/internal/client/dom/elements/misc.js
var rt = !1;
function it() {
	rt || (rt = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[be]?.();
		});
	}, { capture: !0 }));
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function at(e) {
	var t = H, n = G;
	W(null), K(null);
	try {
		return e();
	} finally {
		W(t), K(n);
	}
}
function ot(e, t, n, r = n) {
	e.addEventListener(t, () => at(n));
	let i = e[be];
	e[be] = i ? () => {
		i(), r(!0);
	} : () => r(!0), it();
}
// node_modules/svelte/src/internal/client/reactivity/async.js
function st(e, t, n, r) {
	let i = Xe() ? dt : mt;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = G, c = ct(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				L(e, s);
			}
			lt();
		}
	}
	var d = ut();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ pt(e))).then(u).catch((e) => L(e, s)).finally(d);
	}
	l ? l.then(() => {
		s.f & 16384 ? d() : (c(), f(), lt());
	}) : f();
}
function ct() {
	var e = G, t = H, n = E, r = k;
	return function(i = !0) {
		K(e), W(t), Ke(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function lt(e = !0) {
	K(null), W(null), Ke(null), e && k?.deactivate();
}
function ut() {
	var e = G, t = e.b, n = k, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function dt(e) {
	var t = 2 | y;
	return G !== null && (G.f |= x), {
		ctx: E,
		deps: null,
		effects: null,
		equals: je,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: r,
		wv: 0,
		parent: G,
		ac: null
	};
}
var ft = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function pt(e, t, n) {
	let i = G;
	i === null && Fe();
	var a = void 0, o = Rt(r), s = !H, c = /* @__PURE__ */ new Set();
	return vn(() => {
		var t = G, n = ne();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== xe && n.reject(e);
			}).finally(lt);
		} catch (e) {
			n.reject(e), lt();
		}
		var r = k;
		if (s) {
			if (t.f & 32768) var l = ut();
			if (i.b?.is_rendered()) r.async_deriveds.get(t)?.reject(ft);
			else for (let e of c.values()) e.reject(ft);
			c.add(n), r.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== ft && (r.activate(), t ? (o.f |= de, Ht(o, t)) : (o.f & 8388608 && (o.f ^= de), Ht(o, e)), r.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), dn(() => {
		for (let e of c) e.reject(ft);
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
function mt(e) {
	let t = /* @__PURE__ */ dt(e);
	return t.equals = Ne, t;
}
function ht(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) B(t[n]);
	}
}
function gt(e) {
	var t, n = G, i = e.parent;
	if (!V && i !== null && e.v !== r && i.f & 24576) return Ce(), e.v;
	K(i);
	try {
		ht(e), t = Un(e);
	} finally {
		K(n);
	}
	return t;
}
function _t(e) {
	var t = gt(e);
	!e.equals(t) && (e.wv = Bn(), (!k?.is_fork || e.deps === null) && (k === null ? e.v = t : (k.capture(e, t, !0), xt?.capture(e, t, !0)), e.deps === null)) ? O(e, v) : V || (A === null ? tt(e) : (un() || k?.is_fork) && A.set(e, t));
}
function vt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && at(() => {
		t.ac.abort(xe), t.ac = null;
	}), t.fn !== null && (t.teardown = g), Kn(t, 0), Cn(t));
}
function yt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && qn(t);
}
// node_modules/svelte/src/internal/client/reactivity/batch.js
var bt = null, k = null, xt = null, A = null, St = null, Ct = !1, wt = !1, Tt = null, Et = null, Dt = 0, Ot = 1, kt = class e {
	id = Ot++;
	started = !1;
	linked = !0;
	prev = null;
	next = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#e = /* @__PURE__ */ new Set();
	#t = /* @__PURE__ */ new Set();
	#n = 0;
	#r = /* @__PURE__ */ new Map();
	#i = null;
	#a = [];
	#o = [];
	#s = /* @__PURE__ */ new Map();
	#c = /* @__PURE__ */ new Map();
	#l = /* @__PURE__ */ new Set();
	is_fork = !1;
	#u = !1;
	constructor() {
		bt === null ? bt = this : (bt.next = this, this.prev = bt), bt = this;
	}
	#d() {
		if (this.is_fork) return !0;
		for (let e of this.#r.keys()) if (!this.#f(e)) return !0;
		return !1;
	}
	#f(e) {
		for (var t = e; t !== null; t = t.parent) if (this.#c.has(t)) return !0;
		return !1;
	}
	skip_effect(e) {
		this.#c.has(e) || this.#c.set(e, {
			d: [],
			m: []
		}), this.#l.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#c.get(e);
		if (n) {
			this.#c.delete(e);
			for (var r of n.d) O(r, y), t(r);
			for (r of n.m) O(r, b), t(r);
		}
		this.#l.add(e);
	}
	#p() {
		var e = [];
		for (let i of this.#a) if (!(i.f & 16384 || !(i.f & 6144))) {
			for (var t = i, n = !1; t.parent !== null;) {
				t = t.parent;
				var r = t.f;
				if (r & 96) {
					if (!(r & 1024)) {
						n = !0;
						break;
					}
					t.f ^= v;
				}
			}
			n || e.push(t);
		}
		return this.#a = [], e;
	}
	#m() {
		this.started = !0;
		for (let [e, t] of this.#s) O(e, t), this.schedule(e);
		this.apply();
		for (var t = Tt = [], n = [], r = Et = []; this.#a.length > 0;) {
			Dt++ > 1e3 && (this.#b(), jt());
			for (let e of this.#p()) try {
				this.#h(e, t, n);
			} catch (t) {
				throw Ft(e), this.#d() || this.discard(), t;
			}
			if (this.#a.length > 0) {
				for (let e of n) this.#a.push(e);
				for (let e of t) this.#a.push(e);
				n.length = 0, t.length = 0;
			}
		}
		if (k = null, r.length > 0) {
			var i = e.ensure();
			for (let e of r) i.schedule(e);
		}
		if (Tt = null, Et = null, this.#d()) {
			this.#y(n), this.#y(t);
			for (let [e, t] of this.#c) Pt(e, t);
			r.length > 0 && k.#m();
			return;
		}
		let a = this.#g();
		if (a) this.#y(n), this.#y(t), a.#v(this);
		else {
			this.#s.clear();
			for (let e of this.#e) e(this);
			this.#e.clear(), xt = this, Mt(n), Mt(t), xt = null, this.#i?.resolve();
			var o = k;
			this.#n === 0 && (this.#a.length === 0 || o !== null) && this.#b(), o !== null && (M.clear(), o.#m());
		}
	}
	#h(e, t, n) {
		e.f ^= v;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = !!(i & 96);
			if (!(a && i & 1024 || i & 8192 || this.#c.has(r)) && r.fn !== null) {
				a ? r.f ^= v : i & 4 ? t.push(r) : Vn(r) && (i & 16 && this.add_dirty_reaction(r, b), qn(r));
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
	#g() {
		for (var e = this.prev; e !== null; e = e.prev) if (!e.is_fork && this.#_(e)) return e;
		return null;
	}
	#_(e) {
		for (let [t, [, n]] of this.current) if (!n && e.current.has(t)) return !0;
		return !1;
	}
	#v(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve).catch(e.reject);
		}
		e.async_deriveds.clear(), this.transfer_reactions(e.#s);
		let t = (e) => {
			var n = e.reactions;
			if (n !== null && !(e.f & 2 && !(e.f & 6144))) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#s.delete(i), O(i, y), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#b(), k = this, this.#m();
	}
	#y(e) {
		for (var t = 0; t < e.length; t += 1) nt(e[t], this.#s);
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
			wt = !0, k = this, this.#m();
		} finally {
			Dt = 0, St = null, Tt = null, Et = null, wt = !1, k = null, A = null, M.clear();
		}
	}
	discard() {
		for (let e of this.#t) e(this);
		this.#t.clear();
		for (let e of this.async_deriveds.values()) e.reject(ft);
		this.#b(), this.#i?.resolve();
	}
	register_created_effect(e) {
		this.#o.push(e);
	}
	increment(e, t) {
		if (this.#n += 1, e) {
			let e = this.#r.get(t) ?? 0;
			this.#r.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#n, e) {
			let e = this.#r.get(t) ?? 0;
			e === 1 ? this.#r.delete(t) : this.#r.set(t, e - 1);
		}
		this.#u || (this.#u = !0, D(() => {
			this.#u = !1, this.linked && this.flush();
		}));
	}
	transfer_reactions(e) {
		for (let [t, n] of e) this.add_dirty_reaction(t, n);
		e.clear();
	}
	add_dirty_reaction(e, t) {
		(t === 2048 || this.#s.get(e) !== 2048) && this.#s.set(e, t);
	}
	oncommit(e) {
		this.#e.add(e);
	}
	ondiscard(e) {
		this.#t.add(e);
	}
	settled() {
		return (this.#i ??= ne()).promise;
	}
	static ensure() {
		if (k === null) {
			let t = k = new e();
			!wt && !Ct && D(() => {
				t.started || t.flush();
			});
		}
		return k;
	}
	apply() {
		A = null;
	}
	schedule(e) {
		St = e, e.b?.is_pending && e.f & 16777228 && !(e.f & 32768) ? e.b.defer_effect(e) : this.#a.push(e);
	}
	#b() {
		if (this.linked) {
			var e = this.prev, t = this.next;
			e === null || (e.next = t), t === null ? bt = e : t.prev = e, this.linked = !1;
		}
	}
};
function At(e) {
	var t = Ct, n = xt;
	xt = null, Ct = !0;
	try {
		var r;
		for (e && (At(), r = e());;) {
			if ($e(), k === null) return r;
			k.flush();
		}
	} finally {
		Ct = t, xt = n;
	}
}
function jt() {
	try {
		ze();
	} catch (e) {
		L(e, St);
	}
}
var j = null;
function Mt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Vn(r) && (j = /* @__PURE__ */ new Set(), qn(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && En(r), j?.size > 0)) {
				M.clear();
				for (let e of j) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) j.has(n) && (j.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || qn(n);
					}
				}
				j.clear();
			}
		}
		j = null;
	}
}
function Nt(e) {
	k.schedule(e);
}
function Pt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), O(e, v);
		for (var n = e.first; n !== null;) Pt(n, t), n = n.next;
	}
}
function Ft(e) {
	O(e, v);
	for (var t = e.first; t !== null;) Ft(t), t = t.next;
}
// node_modules/svelte/src/internal/client/reactivity/sources.js
var It = /* @__PURE__ */ new Set(), M = /* @__PURE__ */ new Map(), Lt = !1;
function Rt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: je,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function zt(e, t) {
	let n = Rt(e, t);
	return Pn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function N(t, n = !1, r = !0) {
	let i = Rt(t);
	return n || (i.equals = Ne), e && r && E !== null && E.l !== null && (E.l.s ??= []).push(i), i;
}
function P(e, t, n = !1) {
	return H !== null && (!U || H.f & 131072) && Xe() && H.f & 4325394 && (q === null || !q.has(e)) && We(), Ht(e, n ? Kt(t) : t, Et);
}
var Bt = null, Vt = 0;
function Ht(e, t, n = null) {
	if (!e.equals(t)) {
		V ? M.set(e, t) : M.has(e) || M.set(e, e.v);
		var r = kt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && gt(t), A === null && tt(t);
		}
		e.wv = Bn(), Bt = null, Vt = 0, Gt(e, y, n), Bt = null, Xe() && G !== null && G.f & 1024 && !(G.f & 96) && (X === null ? Fn([e]) : X.push(e)), !r.is_fork && It.size > 0 && !Lt && Ut();
	}
	return t;
}
function Ut() {
	Lt = !1;
	for (let e of It) {
		e.f & 1024 && O(e, b);
		let t;
		try {
			t = Vn(e);
		} catch {
			t = !0;
		}
		t && qn(e);
	}
	It.clear();
}
function Wt(e) {
	P(e, e.v + 1);
}
function Gt(e, t, n) {
	var r = e.reactions;
	if (r !== null) {
		var i = Xe(), a = r.length;
		if (Vt += a, Vt > 1e5 && Bt === null && (Bt = /* @__PURE__ */ new Set()), Bt !== null) {
			if (Bt.has(e)) return;
			Bt.add(e);
		}
		for (var o = 0; o < a; o++) {
			var s = r[o], c = s.f;
			if (i || s !== G) {
				var l = (c & y) === 0;
				if (l && O(s, t), c & 131072) It.add(s);
				else if (c & 2) {
					var u = s;
					A?.delete(u), Gt(u, b, n);
				} else if (l) {
					var d = s;
					c & 16 && j !== null && j.add(d), n === null ? Nt(d) : n.push(d);
				}
			}
		}
	}
}
function Kt(e) {
	if (typeof e != "object" || !e || fe in e || pe in e) return e;
	let t = h(e);
	if (t !== p && t !== m) return e;
	var n = /* @__PURE__ */ new Map(), i = a(e), o = /* @__PURE__ */ zt(0), s = null, c = Rn, l = (e) => {
		if (Rn === c) return e();
		var t = H, n = Rn;
		W(null), zn(c);
		var r = e();
		return W(t), zn(n), r;
	};
	return i && n.set("length", /* @__PURE__ */ zt(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			"value" in r && r.configurable !== !1 && r.enumerable !== !1 && r.writable !== !1 || He();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ zt(r.value, s);
				return n.set(t, e), e;
			}) : P(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var i = n.get(t);
			if (i === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ zt(r, s));
					n.set(t, e), Wt(o);
				}
			} else P(i, r), Wt(o);
			return !0;
		},
		get(t, i, a) {
			if (i === fe) return e;
			var o = n.get(i), c = i in t;
			if (o === void 0 && (!c || d(t, i)?.writable) && (o = l(() => /* @__PURE__ */ zt(Kt(c ? t[i] : r), s)), n.set(i, o)), o !== void 0) {
				var u = Z(o);
				return u === r ? void 0 : u;
			}
			return Reflect.get(t, i, a);
		},
		getOwnPropertyDescriptor(e, t) {
			this.has?.(e, t);
			var i = Reflect.getOwnPropertyDescriptor(e, t), a = n.get(t);
			if (a !== void 0) {
				var o = Z(a);
				if (o === r) return;
				if (i && "value" in i) i.value = o;
				else return {
					enumerable: !0,
					configurable: !0,
					value: o,
					writable: !0
				};
			}
			return i;
		},
		has(e, t) {
			if (t === fe) return !0;
			var i = n.get(t), a = i !== void 0 && i.v !== r || Reflect.has(e, t);
			return (i !== void 0 || (G !== null || H !== null) && (!a || d(e, t)?.writable)) && (i === void 0 && (i = l(() => /* @__PURE__ */ zt(a ? Kt(e[t]) : r, s)), n.set(t, i)), Z(i) === r) ? !1 : a;
		},
		set(e, t, a, c) {
			var u = n.get(t), f = t in e;
			if (i && t === "length") for (var p = a; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ zt(r, s)), n.set(p + "", m)) : P(m, r);
			}
			if (u === void 0) (!f || d(e, t)?.writable) && (u = l(() => /* @__PURE__ */ zt(void 0, s)), P(u, Kt(a)), n.set(t, u));
			else {
				f = u.v !== r;
				var h = l(() => Kt(a));
				P(u, h);
			}
			var ee = Reflect.getOwnPropertyDescriptor(e, t);
			if (ee?.set && ee.set.call(c, a), !f) {
				if (i && typeof t == "string") {
					var g = n.get("length"), te = Number(t);
					Number.isInteger(te) && te >= g.v && P(g, te + 1);
				}
				Wt(o);
			}
			return !0;
		},
		ownKeys(e) {
			Z(o);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== r;
			});
			for (var [i, a] of n) a.v !== r && !(i in e) && t.push(i);
			return t;
		},
		setPrototypeOf() {
			Ue();
		}
	});
}
var qt, Jt, Yt, Xt;
function Zt() {
	if (qt === void 0) {
		qt = window, Jt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Yt = d(t, "firstChild").get, Xt = d(t, "nextSibling").get, ee(e) && (e[_e] = void 0, e[ge] = null, e[ve] = void 0, e.__e = void 0), ee(n) && (n[ye] = void 0);
	}
}
function Qt(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function $t(e) {
	return Yt.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function en(e) {
	return Xt.call(e);
}
function F(e, t) {
	if (!S) return /* @__PURE__ */ $t(e);
	var n = /* @__PURE__ */ $t(C);
	if (n === null) n = C.appendChild(Qt());
	else if (t && n.nodeType !== 3) {
		var r = Qt();
		return n?.before(r), w(r), r;
	}
	return t && on(n), w(n), n;
}
function tn(e, t = !1) {
	if (!S) return /* @__PURE__ */ $t(e);
	var n = F(e, t);
	return T(e), n;
}
function I(e, t = 1, n = !1) {
	let r = S ? C : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ en(r);
	if (!S) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = Qt();
			return r === null ? i?.after(a) : r.before(a), w(a), a;
		}
		on(r);
	}
	return w(r), r;
}
function nn(e) {
	e.textContent = "";
}
function rn() {
	return !1;
}
function an(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function on(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
function sn(e) {
	var t = G;
	if (t === null) return H.f |= de, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	L(e, t);
}
function L(e, t) {
	if (e === n) throw e;
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
// node_modules/svelte/src/internal/client/reactivity/effects.js
function cn(e) {
	G === null && (H === null && Re(e), Le()), V && Ie(e);
}
function ln(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function R(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= re);
	var r = {
		ctx: E,
		deps: null,
		nodes: null,
		f: e | y | 512,
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
	if (e & 4) Tt === null ? kt.ensure().schedule(r) : Tt.push(r);
	else if (t !== null) {
		try {
			qn(r);
		} catch (e) {
			throw B(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= se));
	}
	if (i !== null && (i.parent = n, n !== null && ln(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function un() {
	return H !== null && !U;
}
function dn(e) {
	let t = R(8, null);
	return O(t, v), t.teardown = e, t;
}
function fn(e) {
	cn("$effect");
	var t = G.f;
	if (!H && t & 32 && E !== null && !E.i) {
		var n = E;
		(n.e ??= []).push(e);
	} else return pn(e);
}
function pn(e) {
	return R(4 | ce, e);
}
function mn(e) {
	return cn("$effect.pre"), R(8 | ce, e);
}
function hn(e) {
	kt.ensure();
	let t = R(64 | x, e);
	return () => {
		B(t);
	};
}
function gn(e) {
	kt.ensure();
	let t = R(64 | x, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Dn(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function _n(e) {
	return R(4, e);
}
function vn(e) {
	return R(ue | x, e);
}
function yn(e, t = 0) {
	return R(8 | t, e);
}
function bn(e, t = [], n = [], r = []) {
	st(r, t, n, (t) => {
		R(8, () => {
			e(...t.map(Z));
		});
	});
}
function xn(e, t = 0) {
	return R(16 | t, e);
}
function z(e) {
	return R(32 | x, e);
}
function Sn(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = V, r = H;
		Nn(!0), W(null);
		try {
			t.call(null);
		} catch (t) {
			L(t, e.parent);
		} finally {
			Nn(n), W(r);
		}
	}
}
function Cn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && at(() => {
			e.abort(xe);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function wn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Tn(e.nodes.start, e.nodes.end), n = !0), e.f |= oe, Cn(e, t && !n), Kn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Sn(e), e.f ^= oe, e.f |= ie;
	var i = e.parent;
	i !== null && i.first !== null && En(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Tn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ en(e);
		e.remove(), e = n;
	}
}
function En(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Dn(e, t, n = !0) {
	var r = [];
	e.f |= 256, On(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function On(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= re;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = !!(i.f & 65536) || !!(i.f & 32) && !!(e.f & 16);
				On(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function kn(e) {
	e.f &= -257, An(e, !0);
}
function An(e, t) {
	if (!(e.f & 256) && e.f & 8192) {
		e.f ^= re, e.f & 1024 || (O(e, y), kt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = !!(n.f & 65536) || !!(n.f & 32);
			An(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function jn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ en(n);
		t.append(n), n = i;
	}
}
// node_modules/svelte/src/internal/client/legacy.js
var Mn = null, V = !1;
function Nn(e) {
	V = e;
}
var H = null, U = !1;
function W(e) {
	H = e;
}
var G = null;
function K(e) {
	G = e;
}
var q = null;
function Pn(e) {
	H !== null && (H.f & 2097152 || H.f & 2) && (q ??= /* @__PURE__ */ new Set()).add(e);
}
var J = null, Y = 0, X = null;
function Fn(e) {
	X = e;
}
var In = 1, Ln = 0, Rn = Ln;
function zn(e) {
	Rn = e;
}
function Bn() {
	return ++In;
}
function Vn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Vn(a) && _t(a), a.wv > e.wv) return !0;
		}
		t & 512 && A === null && O(e, v);
	}
	return !1;
}
function Hn(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(q !== null && q.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? Hn(a, t, !1) : t === a && (n ? O(a, y) : a.f & 1024 && O(a, b), Nt(a));
	}
}
function Un(e) {
	var t = J, n = Y, r = X, i = H, a = q, o = E, s = U, c = Rn, l = e.f;
	J = null, Y = 0, X = null, H = l & 96 ? null : e, q = null, Ke(e.ctx), U = !1, Rn = ++Ln, e.ac !== null && (at(() => {
		e.ac.abort(xe);
	}), e.ac = null);
	try {
		e.f |= le;
		var u = e.fn, d = u();
		e.f |= ae;
		var f = Wn(e);
		if (Xe() && X !== null && !U && f !== null && !(e.f & 6146)) for (var p = 0; p < X.length; p++) Hn(X[p], e);
		if (i !== null && i !== e) {
			if (Ln++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Ln;
			if (t !== null) for (let e of t) e.rv = Ln;
			X !== null && (r === null ? r = X : r.push(...X));
		}
		return e.f & 8388608 && (e.f ^= de), d;
	} catch (t) {
		return Wn(e), sn(t);
	} finally {
		e.f ^= le, J = t, Y = n, X = r, H = i, q = a, Ke(o), U = s, Rn = c;
	}
}
function Wn(e) {
	var t = e.deps, n = k?.is_fork;
	if (J !== null) {
		var r;
		if (n || Kn(e, Y), t !== null && Y > 0) for (t.length = Y + J.length, r = 0; r < J.length; r++) t[Y + r] = J[r];
		else e.deps = t = J;
		if (un() && e.f & 512) for (r = Y; r < t.length; r++) (t[r].reactions ??= []).push(e);
	} else !n && t !== null && Y < t.length && (Kn(e, Y), t.length = Y);
	return t;
}
function Gn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var i = o.call(n, e);
		if (i !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[i] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (J === null || !s.call(J, t))) {
		var c = t;
		c.f & 512 && (c.f ^= 512), c.v !== r && tt(c), c.ac !== null && at(() => {
			c.ac.abort(xe), c.ac = null, O(c, y);
		}), vt(c), Kn(c, 0);
	}
}
function Kn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Gn(e, n[r]);
}
function qn(e) {
	var t = e.f;
	if (!(t & 16384)) {
		O(e, v);
		var n = G;
		G = e;
		try {
			t & 16777232 ? wn(e) : Cn(e), Sn(e);
			var r = Un(e);
			e.teardown = typeof r == "function" ? r : null, e.wv = In;
		} finally {
			G = n;
		}
	}
}
async function Jn() {
	await Promise.resolve(), At();
}
function Z(e) {
	var t = !!(e.f & 2);
	if (Mn?.add(e), H !== null && !U && !(G !== null && G.f & 16384) && (q === null || !q.has(e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < Ln && (e.rv = Ln, J === null && n !== null && n[Y] === e ? Y++ : J === null ? J = [e] : J.push(e));
		else {
			H.deps ??= [], s.call(H.deps, e) || H.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : s.call(r, H) || r.push(H);
		}
	}
	if (V && M.has(e)) return M.get(e);
	if (t) {
		var i = e;
		if (V) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || Xn(i)) && (a = gt(i)), M.set(i, a), a;
		}
		var o = !(i.f & 512) && !U && H !== null && !!(H.f & 512), c = (i.f & ae) === 0;
		Vn(i) && (o && (i.f |= 512), _t(i)), o && !c && (yt(i), Yn(i));
	}
	if (A?.has(e)) return A.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function Yn(e) {
	if (e.f |= 512, e.deps !== null) for (let n of e.deps) {
		var t = n.reactions;
		t === null ? n.reactions = [e] : s.call(t, e) || t.push(e), n.f & 2 && !(n.f & 512) && (yt(n), Yn(n));
	}
}
function Xn(e) {
	if (e.v === r) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (M.has(t) || t.f & 2 && Xn(t)) return !0;
	return !1;
}
function Zn(e) {
	var t = U;
	try {
		return U = !0, e();
	} finally {
		U = t;
	}
}
function Qn(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (fe in e) $n(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && fe in n && $n(n);
		}
	}
}
function $n(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			$n(e[n], t);
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
// node_modules/svelte/src/internal/client/dom/elements/events.js
var er = Symbol("events"), tr = /* @__PURE__ */ new Set(), nr = /* @__PURE__ */ new Set();
function rr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || sr.call(t, e), !e.cancelBubble) return at(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? (i.__removed = !1, D(() => {
		i.__removed || t.addEventListener(e, i, r);
	})) : t.addEventListener(e, i, r), i;
}
function ir(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = rr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && dn(() => {
		o.__removed = !0, t.removeEventListener(e, o, a);
	});
}
var ar = null, or = !1;
function sr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	ar = e, or || (or = !0, setTimeout(() => {
		or = !1, ar = null;
	}));
	var o = 0, s = ar === e && e[er];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[er] = t;
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
		var d = H, f = G;
		W(null), K(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[er]?.[r];
					h == null || a.disabled && e.target !== a || h.call(a, e);
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
			e[er] = t, delete e.currentTarget, W(d), K(f);
		}
	}
}
// node_modules/svelte/src/internal/client/dom/reconciler.js
var cr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function lr(e) {
	return cr?.createHTML(e) ?? e;
}
function ur(e) {
	var t = an("template");
	return t.innerHTML = lr(e.replaceAll("<!>", "<!---->")), t.content;
}
// node_modules/svelte/src/internal/client/dom/template.js
function dr(e, t) {
	var n = G;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Q(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (S) return dr(C, null), C;
		i === void 0 && (i = ur(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ $t(i)));
		var t = r || Jt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ $t(t), s = t.lastChild;
			dr(o, s);
		} else dr(t, t);
		return t;
	};
}
function $(e, t) {
	if (S) {
		var n = G;
		n.f & 32768 && n.nodes.end !== null || (n.nodes.end = C), De();
	} else e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var fr = ["touchstart", "touchmove"];
function pr(e) {
	return fr.includes(e);
}
// node_modules/svelte/src/reactivity/create-subscriber.js
function mr(e) {
	let t = 0, n = Rt(0), r;
	return () => {
		un() && (Z(n), yn(() => (t === 0 && (r = Zn(() => e(() => Wt(n)))), t += 1, () => {
			D(() => {
				--t, t === 0 && (r?.(), r = void 0, Wt(n));
			});
		})));
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var hr = se | x;
function gr(e, t, n, r) {
	new _r(e, t, n, r);
}
var _r = class {
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
	#f = /* @__PURE__ */ new Map();
	#p = null;
	#m = mr(() => (this.#p = Rt(this.#l), () => {
		this.#p = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = xn(() => {
			if (S) {
				let e = Ae(this.#t);
				De();
				let t = e === "[!";
				if (e.startsWith("[?")) {
					let t = JSON.parse(e.slice(2));
					this.#g(t);
				} else t ? this.#y() : this.#h();
			} else this.#b();
		}, hr), S && (this.#e = C);
	}
	#h() {
		try {
			this.#a = z(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#g(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#_(e);
		D(r), t && (this.#s = z(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#_(e) {
		var t = !1, n = !1;
		let r = () => {
			this.#v() || (t ? Te() : (t = !0, n && Ge(), this.#s !== null && Dn(this.#s, () => {
				this.#s = null;
			}), this.#S(() => {
				this.#b();
			})));
		};
		return {
			reset: r,
			invoke_onerror: () => {
				if (!this.#v()) try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					L(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#v() {
		return (this.#i.f & (ie | oe)) !== 0;
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = z(() => e(this.#e)), D(() => {
			if (!this.#v()) {
				var e = this.#c = document.createDocumentFragment(), t = Qt(), n = !1;
				e.append(t), this.#a = this.#S(() => {
					try {
						return z(() => this.#r(t));
					} catch (e) {
						try {
							this.error(e), n = !0;
						} catch (e) {
							L(e, this.#i.parent);
						}
						return null;
					}
				}), this.#a === null ? (this.#c = null, n && this.#x(k)) : this.#u === 0 && (this.#e.before(e), this.#c = null, Dn(this.#o, () => {
					this.#o = null;
				}), this.#x(k));
			}
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = z(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				jn(this.#a, e);
				let t = this.#n.pending;
				this.#o = z(() => t(this.#e));
			} else this.#x(k);
		} catch (e) {
			this.error(e);
		}
	}
	#x(e) {
		this.is_pending = !1, e.transfer_reactions(this.#f);
	}
	defer_effect(e) {
		nt(e, this.#f);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#S(e) {
		var t = G, n = H, r = E;
		K(this.#i), W(this.#i), Ke(this.#i.ctx);
		try {
			return kt.ensure(), e();
		} finally {
			K(t), W(n), Ke(r);
		}
	}
	#C(e, t) {
		this.has_pending_snippet() ? (this.#u += e, this.#u === 0 && (this.#x(t), this.#o && Dn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null))) : this.parent && this.parent.#C(e, t);
	}
	update_pending_count(e, t) {
		this.#C(e, t), this.#l += e, !this.#p || this.#d || (this.#d = !0, D(() => {
			this.#d = !1, this.#p && Ht(this.#p, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#m(), Z(this.#p);
	}
	error(e) {
		if (e === n || !this.#n.onerror && !this.#n.failed) throw e;
		k?.is_fork ? (this.#a && k.skip_effect(this.#a), this.#o && k.skip_effect(this.#o), this.#s && k.skip_effect(this.#s), k.oncommit(() => {
			this.#v() || this.#w(e);
		})) : this.#w(e);
	}
	#w(e) {
		this.#a &&= (B(this.#a), null), this.#o &&= (B(this.#o), null), this.#s &&= (B(this.#s), null), S && (w(this.#t), Oe(), w(ke()));
		let t = this.#n.failed, n = (e) => {
			if (this.#v()) return;
			let { reset: n, invoke_onerror: r } = this.#_(e);
			r(), t && !this.#v() && (this.#s = this.#S(() => {
				try {
					return z(() => {
						var r = G;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return L(e, this.#i.parent), null;
				}
			}));
		};
		D(() => {
			if (!this.#v()) {
				var t;
				try {
					t = this.transform_error(e);
				} catch (e) {
					L(e, this.#i && this.#i.parent);
					return;
				}
				typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => L(e, this.#i && this.#i.parent)) : n(t);
			}
		});
	}
};
function vr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[ye] ??= e.nodeValue) && (e[ye] = n, e.nodeValue = `${n}`);
}
function yr(e, t) {
	return Sr(e, t);
}
function br(e, t) {
	Zt(), t.intro = t.intro ?? !1;
	let r = t.target, i = S, a = C;
	try {
		for (var o = /* @__PURE__ */ $t(r); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ en(o);
		if (!o) throw n;
		Ee(!0), w(o);
		let i = Sr(e, {
			...t,
			anchor: o
		});
		return Ee(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== n && console.warn("Failed to hydrate: ", i), t.recover === !1 && Be(), Zt(), nn(r), Ee(!1), yr(e, t);
	} finally {
		Ee(i), w(a);
	}
}
var xr = /* @__PURE__ */ new Map();
function Sr(e, { target: t, anchor: r, props: i = {}, events: a, context: o, intro: s = !0, transformError: l }) {
	Zt();
	var u = void 0, d = gn(() => {
		var s = r ?? t.appendChild(Qt());
		gr(s, { pending: () => {} }, (t) => {
			qe({});
			var r = E;
			if (o && (r.c = o), a && (i.$$events = a), S && dr(t, null), u = e(t, i) || Ye(), S && (G.nodes.end = C, C === null || C.nodeType !== 8 || C.data !== "]")) throw we(), n;
			Je();
		}, l);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = pr(r);
					for (let e of [t, document]) {
						var a = xr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), xr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, sr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(c(tr)), nr.add(f), () => {
			for (var e of d) for (let r of [t, document]) {
				var n = xr.get(r), i = n.get(e);
				--i == 0 ? (r.removeEventListener(e, sr), n.delete(e), n.size === 0 && xr.delete(r)) : n.set(e, i);
			}
			nr.delete(f), s !== r && s.parentNode?.removeChild(s);
		};
	});
	return Cr.set(u, d), u;
}
var Cr = /* @__PURE__ */ new WeakMap();
function wr(e, t) {
	let n = Cr.get(e);
	return n ? (Cr.delete(e), n(t)) : Promise.resolve();
}
// node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Tr = class {
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
			if (n) kn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (kn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
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
						jn(r, t), t.append(Qt()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Dn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = k, r = rn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = document.createDocumentFragment(), a = Qt();
				i.append(a), this.#n.set(e, {
					effect: z(() => t(a)),
					fragment: i
				});
			} else this.#t.set(e, z(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else S && (this.anchor = C), this.#a(n);
	}
};
function Er(t) {
	E === null && Pe("onMount"), e && E.l !== null ? Dr(E).m.push(t) : fn(() => {
		let e = Zn(t);
		if (typeof e == "function") return e;
	});
}
function Dr(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/if.js
function Or(e, t, n = !1) {
	var r;
	S && (r = C, De());
	var i = new Tr(e), a = n ? se : 0;
	function o(e, t) {
		if (S) {
			var n = Ae(r);
			if (e !== parseInt(n.substring(1))) {
				var a = ke();
				w(a), i.anchor = a, Ee(!1), i.ensure(e, t), Ee(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	xn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
// node_modules/svelte/src/internal/client/dom/css.js
function kr(e, t) {
	_n(() => {
		e = G?.parent?.nodes?.start ?? e;
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = an("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
// node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Ar = Symbol("is custom element"), jr = Symbol("is html"), Mr = Se ? "link" : "LINK";
function Nr(e) {
	if (S) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Pr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Pr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[be] = n, D(n), it();
	}
}
function Pr(e, t, n, r) {
	var i = Fr(e);
	if (!(S && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Mr))) {
		var a = i[t];
		a !== (i[t] = n) && (t === "loading" && (e[he] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Lr(e).has(t) ? e[t] = n : (!S || typeof n != "number" && typeof n != "boolean" || a !== String(n)) && e.setAttribute(t, n));
	}
}
function Fr(e) {
	return e[ge] ??= {
		[Ar]: e.nodeName.includes("-"),
		[jr]: e.namespaceURI === i
	};
}
var Ir = /* @__PURE__ */ new Map();
function Lr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Ir.get(t);
	if (n) return n;
	Ir.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = f(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.add(o);
		i = h(i);
	}
	return n;
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Rr(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	ot(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = zr(e) ? Br(a) : a, n(a), k !== null && r.add(k), await Jn(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (S && e.defaultValue !== e.value || Zn(t) == null && e.value) && (n(zr(e) ? Br(e.value) : e.value), k !== null && r.add(k)), yn(() => {
		var n = t();
		if (e === document.activeElement) {
			var i = k;
			if (r.has(i)) return;
		}
		zr(e) && n === Br(e.value) || (e.type !== "date" || n || e.value) && n !== e.value && (e.value = n ?? "");
	});
}
function zr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Br(e) {
	return e === "" ? null : +e;
}
// node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Vr(e = !1) {
	let t = E, n = t.l.u;
	if (!n) return;
	let r = () => Qn(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ dt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Z(i);
	}
	n.b.length && mn(() => {
		Hr(t, r), _(n.b);
	}), fn(() => {
		let e = Zn(() => n.m.map(te));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && fn(() => {
		Hr(t, r), _(n.a);
	});
}
function Hr(e, t) {
	if (e.l.s) for (let t of e.l.s) Z(t);
	t();
}
// node_modules/svelte/src/internal/client/reactivity/store.js
var Ur = !1;
function Wr(e) {
	var t = Ur;
	try {
		return Ur = !1, [e(), Ur];
	} finally {
		Ur = t;
	}
}
// node_modules/svelte/src/internal/client/reactivity/props.js
function Gr(t, n, r, i) {
	var a = !e || !!(r & 2), o = !!(r & 8), s = !!(r & 16), c = i, l = !0, u = void 0, f = () => s && a ? (u ??= /* @__PURE__ */ dt(i), Z(u)) : (l && (l = !1, c = s ? Zn(i) : i), c);
	let p;
	if (o) {
		var m = fe in t || me in t;
		p = d(t, n)?.set ?? (m && n in t ? (e) => t[n] = e : void 0);
	}
	var h, ee = !1;
	o ? [h, ee] = Wr(() => t[n]) : h = t[n], h === void 0 && i !== void 0 && (h = f(), p && (a && Ve(n), p(h)));
	var g = a ? () => {
		var e = t[n];
		return e === void 0 ? f() : (l = !0, e);
	} : () => {
		var e = t[n];
		return e !== void 0 && (c = void 0), e === void 0 ? c : e;
	};
	if (a && !(r & 4)) return g;
	if (p) {
		var te = t.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || te || ee) && p(t ? g() : e), e) : g();
		});
	}
	var _ = !1, ne = (r & 1 ? dt : mt)(() => (_ = !1, g()));
	o && Z(ne);
	var v = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Z(ne) : a && o ? Kt(e) : e;
			return P(ne, n), _ = !0, c !== void 0 && (c = n), e;
		}
		return V && _ || v.f & 16384 ? ne.v : Z(ne);
	});
}
// node_modules/svelte/src/legacy/legacy-client.js
function Kr(e) {
	return new qr(e);
}
var qr = class {
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
				return Z(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === me || (Z(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return P(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		});
		this.#t = (e.hydrate ? br : yr)(e.component, {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		}), e?.props?.$$host && e.sync !== !1 || At(), this.#e = r.$$events;
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
			wr(this.#t);
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
}, Jr;
typeof HTMLElement == "function" && (Jr = class extends HTMLElement {
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
					let n = an("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = Xr(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = Yr(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = Kr({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = hn(() => {
				yn(() => {
					this.$$r = !0;
					for (let e of l(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = Yr(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = Yr(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
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
function Yr(e, t, n, r) {
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
function Xr(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function Zr(e, t, n, r, i, a) {
	let o = class extends Jr {
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
				n = Yr(e, n, t), this.$$d[e] = n;
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
// PlexCard.svelte
var Qr = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-lueg2f\">Active</span>"), $r = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-lueg2f\">Authenticated</span>"), ei = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-lueg2f\">Connected</span>"), ti = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-lueg2f\">Disconnected</span>"), ni = /* @__PURE__ */ Q("<div class=\"loading-state svelte-lueg2f\"><div class=\"spinner svelte-lueg2f\"></div> <span>Linking with Plex Nexus...</span></div>"), ri = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-lueg2f\"> </button>"), ii = /* @__PURE__ */ Q("<button class=\"btn-ghost accent svelte-lueg2f\"> </button>"), ai = /* @__PURE__ */ Q("<button class=\"btn-danger-ghost svelte-lueg2f\">Cancel Authorization</button>"), oi = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-lueg2f\">Switch Account</button>"), si = /* @__PURE__ */ Q("<button class=\"btn-primary plex-btn svelte-lueg2f\"><svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"currentColor\"><path d=\"M12 0L9.33 6.67L2 9.33L7.33 14.67L6 22L12 18.67L18 22L16.67 14.67L22 9.33L14.67 6.67L12 0Z\"></path></svg> Sign in with Plex</button>"), ci = /* @__PURE__ */ Q("<div class=\"settings-section svelte-lueg2f\"><div class=\"form-grid svelte-lueg2f\"><div class=\"form-field svelte-lueg2f\"><span class=\"field-label svelte-lueg2f\">Server Access URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:32400\" class=\"input-field svelte-lueg2f\"/> <span class=\"helper-text svelte-lueg2f\">Typically http://[IP]:32400. Use localhost if running natively.</span></div> <div class=\"form-field svelte-lueg2f\"><span class=\"field-label svelte-lueg2f\">Friendly Name</span> <input type=\"text\" placeholder=\"e.g. Home Media\" class=\"input-field svelte-lueg2f\"/></div> <div class=\"actions-row svelte-lueg2f\"><button class=\"btn-primary svelte-lueg2f\"> </button> <!> <!> <div class=\"auth-box svelte-lueg2f\"><!></div></div></div></div>"), li = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-lueg2f\"><div class=\"card-header svelte-lueg2f\"><div class=\"header-left svelte-lueg2f\"><h2 class=\"card-title svelte-lueg2f\">Plex Media Server</h2> <div class=\"badges svelte-lueg2f\"><!> <!> <!></div></div> <button class=\"btn-ghost-small svelte-lueg2f\"> </button></div> <!></section>"), ui = {
	hash: "svelte-lueg2f",
	code: "\n  /* SHADOW DOM STYLING */.plugin-card.svelte-lueg2f {background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);padding:18px 20px;color:var(--text-primary);font-family:inherit;box-sizing:border-box;}.card-header.svelte-lueg2f {display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle);}.header-left.svelte-lueg2f {display:flex;align-items:center;gap:12px;flex-wrap:wrap;}.card-title.svelte-lueg2f {margin:0;font-size:17px;font-weight:700;letter-spacing:-0.01em;}.badges.svelte-lueg2f {display:flex;gap:6px;}.status-badge.svelte-lueg2f {font-size:9px;padding:2px 8px;border-radius:5px;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;}.status-badge.active.svelte-lueg2f {background:rgba(20, 184, 166, 0.1);color:var(--color-primary);border:1px solid rgba(20, 184, 166, 0.2);}.status-badge.success.svelte-lueg2f {background:rgba(16, 185, 129, 0.1);color:#10b981;border:1px solid rgba(16, 185, 129, 0.2);}.status-badge.warning.svelte-lueg2f {background:rgba(245, 158, 11, 0.1);color:#f59e0b;border:1px solid rgba(245, 158, 11, 0.2);}.btn-ghost.svelte-lueg2f,\n  .btn-ghost-small.svelte-lueg2f,\n  .btn-danger-ghost.svelte-lueg2f {padding:8px 14px;background:rgba(255, 255, 255, 0.04);border:1px solid var(--border-subtle);color:var(--text-primary);border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-ghost-small.svelte-lueg2f {padding:5px 10px;font-size:11px;border-radius:6px;}.btn-ghost.svelte-lueg2f:hover,\n  .btn-ghost-small.svelte-lueg2f:hover {background:rgba(255, 255, 255, 0.08);border-color:rgba(255, 255, 255, 0.2);}.btn-ghost.accent.svelte-lueg2f {color:var(--color-primary);border-color:rgba(20, 184, 166, 0.3);}.btn-danger-ghost.svelte-lueg2f {color:#ef4444;border-color:rgba(239, 68, 68, 0.2);}.btn-primary.svelte-lueg2f {padding:8px 18px;background:var(--color-primary);color:#000;border:none;border-radius:8px;font-weight:700;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-lueg2f:hover:not(:disabled) {filter:brightness(1.1);transform:translateY(-1px);}.plex-btn.svelte-lueg2f {display:flex;align-items:center;gap:8px;background:#e5a00d; /* Plex Gold */color:#000;}.loading-state.svelte-lueg2f {display:flex;flex-direction:column;align-items:center;gap:12px;padding:24px;color:var(--text-muted);}.spinner.svelte-lueg2f {width:24px;height:24px;border:3px solid rgba(255, 255, 255, 0.05);border-top-color:var(--color-primary);border-radius:50%;\n    animation: svelte-lueg2f-spin 1s linear infinite;}\n\n  @keyframes svelte-lueg2f-spin {\n    to {\n      transform: rotate(360deg);\n    }\n  }.settings-section.svelte-lueg2f {margin-top:4px;}.form-grid.svelte-lueg2f {display:grid;grid-template-columns:1fr;gap:12px;}\n  @media (min-width: 640px) {.form-grid.svelte-lueg2f {grid-template-columns:1fr 1fr;}.actions-row.svelte-lueg2f {grid-column:span 2;}}\n  .form-field.svelte-lueg2f {display:flex;flex-direction:column;gap:6px;min-width:0;}.field-label.svelte-lueg2f {font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;}.input-field.svelte-lueg2f {width:100%;min-width:0;box-sizing:border-box;padding:9px 12px;background:var(--bg-input, #0b0f1a);border:1px solid var(--border-subtle);border-radius:8px;color:var(--text-primary);font-size:13px;transition:all 0.2s;}.input-field.svelte-lueg2f:focus {outline:none;border-color:var(--color-primary);box-shadow:0 0 0 3px rgba(20, 184, 166, 0.1);}.helper-text.svelte-lueg2f {font-size:11px;color:var(--text-muted);font-style:italic;}.actions-row.svelte-lueg2f {display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:4px;}.auth-box.svelte-lueg2f {margin-left:auto;}\n\n  @media (max-width: 600px) {.auth-box.svelte-lueg2f {margin-left:0;width:100%;}.auth-box.svelte-lueg2f button:where(.svelte-lueg2f) {width:100%;}\n  }"
};
function di(e, t) {
	qe(t, !1), kr(e, ui);
	let n = Gr(t, "apiBase", 12, ""), r = /* @__PURE__ */ N(""), i = /* @__PURE__ */ N(""), a = /* @__PURE__ */ N(!1), o = /* @__PURE__ */ N(!1), s = /* @__PURE__ */ N(!0), c = /* @__PURE__ */ N(!1), l = /* @__PURE__ */ N(!1), u = /* @__PURE__ */ N(!1), d = null, f = null, p = /* @__PURE__ */ N(!1), m = /* @__PURE__ */ N(!1), h = /* @__PURE__ */ N(!1);
	Er(async () => {
		n(n().replace(/\/$/, "")), await g(), P(s, !1);
	});
	function _getCookie(name) {
		if (typeof document === "undefined") return null;
		let m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
		return m ? decodeURIComponent(m[1]) : null;
	}
	async function _apiFetch(url, opts = {}) {
		let headers = { ...(opts.headers || {}) };
		let csrf = _getCookie("csrf_token") || _getCookie("echo_csrf");
		if (csrf) {
			headers["X-CSRF-Token"] = csrf;
			headers["X-Echo-CSRF"] = csrf;
		}
		return fetch(url, { credentials: "include", ...opts, headers });
	}
	async function ee() {
		try {
			if (P(h, !0), !(await _apiFetch(`${n()}/activate`, { method: "POST" })).ok) throw Error("Activation failed");
			await g();
		} catch (e) {
			console.error("Failed to activate server:", e), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Activation failed. Check logs.",
				type: "error"
			} }));
		} finally {
			P(h, !1);
		}
	}
	async function g() {
		try {
			let e = await (await _apiFetch(`${n()}/settings`)).json();
			e?.settings && (P(r, e.settings.base_url || ""), P(i, e.settings.server_name || ""), P(a, e.settings.has_token || !1), P(o, e.settings.connected || !1), P(m, e.settings.is_active || !1));
		} catch (e) {
			console.error("Failed to load Plex settings:", e);
		}
	}
	async function te() {
		if (!Z(r).trim()) window.dispatchEvent(new CustomEvent("es-toast", { detail: {
			message: "Server URL is required",
			type: "error"
		} }));
		else try {
			if (P(c, !0), !(await _apiFetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					base_url: Z(r),
					server_name: Z(i)
				})
			})).ok) throw Error("Save failed");
			await g(), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Settings saved successfully",
				type: "success"
			} }));
		} catch (e) {
			console.error("Failed to save Plex settings:", e), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Failed to save settings.",
				type: "error"
			} }));
		} finally {
			P(c, !1);
		}
	}
	async function _() {
		try {
			P(u, !0);
			let res = await _apiFetch(`${n()}/auth/start`, { method: "POST" });
			let e = await res.json().catch(() => ({}));
			if (!res.ok || !e?.oauth_url || !e?.session_id) {
				throw Error(e?.error || e?.detail || `Failed to start Plex OAuth (${res.status})`);
			}
			d = e.session_id;
			window.open(e.oauth_url, "PlexOAuth", "width=600,height=700,menubar=no,status=no");
			if (f) clearInterval(f);
			f = setInterval(async () => {
				try {
					let pollRes = await _apiFetch(`${n()}/auth/poll/${d}`);
					if (!pollRes.ok) {
						pollRes.status === 404 && (clearInterval(f), f = null, P(u, !1), d = null);
						return;
					}
					(await pollRes.json())?.completed && (clearInterval(f), f = null, P(u, !1), d = null, await g(), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
						message: "Plex authentication successful!",
						type: "success"
					} })));
				} catch (e) {
					console.error("OAuth poll error:", e);
				}
			}, 3e3);
		} catch (e) {
			console.error("Failed to start Plex OAuth:", e);
			P(u, !1);
			d = null;
			window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: e?.message || "Failed to start Plex authentication.",
				type: "error"
			} }));
		}
	}
	async function ne() {
		if (f) {
			clearInterval(f);
			f = null;
		}
		let sid = d;
		d = null;
		P(u, !1);
		if (sid) {
			try {
				await _apiFetch(`${n()}/auth/cancel/${sid}`, { method: "DELETE" });
			} catch (e) {
				console.error("Failed to cancel OAuth:", e);
			}
		}
	}
	async function v() {
		try {
			P(l, !0), (await (await _apiFetch(`${n()}/test-connection`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ base_url: Z(r) })
			})).json())?.connected ? (window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Connection successful!",
				type: "success"
			} })), await g()) : window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Connection failed. Check URL and ensure Plex is running.",
				type: "error"
			} }));
		} catch (e) {
			console.error("Connection test failed:", e), window.dispatchEvent(new CustomEvent("es-toast", { detail: {
				message: "Test failed with error.",
				type: "error"
			} }));
		} finally {
			P(l, !1);
		}
	}
	var y = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), At();
		}
	};
	Vr();
	var b = li(), re = F(b), ie = F(re), ae = I(F(ie), 2), oe = F(ae), se = (e) => {
		$(e, Qr());
	};
	Or(oe, (e) => {
		Z(m) && e(se);
	});
	var x = I(oe, 2), ce = (e) => {
		$(e, $r());
	};
	Or(x, (e) => {
		Z(a) && e(ce);
	});
	var le = I(x, 2), ue = (e) => {
		$(e, ei());
	}, de = (e) => {
		$(e, ti());
	};
	Or(le, (e) => {
		Z(o) ? e(ue) : Z(a) && e(de, 1);
	}), T(ae), T(ie);
	var fe = I(ie, 2), pe = tn(fe, !0);
	T(re);
	var me = I(re, 2), he = (e) => {
		$(e, ni());
	}, ge = (e) => {
		var t = ci(), n = F(t), o = F(n), s = I(F(o), 2);
		Nr(s), Oe(2), T(o);
		var d = I(o, 2), f = I(F(d), 2);
		Nr(f), T(d);
		var p = I(d, 2), g = F(p), y = tn(g, !0), b = I(g, 2), re = (e) => {
			var t = ri(), n = tn(t, !0);
			bn((e) => {
				t.disabled = e, vr(n, Z(l) ? "Testing..." : "Test Connection");
			}, [() => (Z(l), Z(r), Zn(() => Z(l) || !Z(r).trim()))]), ir("click", t, v), $(e, t);
		};
		Or(b, (e) => {
			Z(a) && e(re);
		});
		var ie = I(b, 2), ae = (e) => {
			var t = ii(), n = tn(t, !0);
			bn(() => {
				t.disabled = Z(h), vr(n, Z(h) ? "Activating..." : "Activate for Sync");
			}), ir("click", t, ee), $(e, t);
		};
		Or(ie, (e) => {
			!Z(m) && Z(a) && e(ae);
		});
		var oe = I(ie, 2), se = F(oe), x = (e) => {
			var t = ai();
			ir("click", t, ne), $(e, t);
		}, ce = (e) => {
			var t = oi();
			ir("click", t, _), $(e, t);
		}, le = (e) => {
			var t = si();
			ir("click", t, _), $(e, t);
		};
		Or(se, (e) => {
			Z(u) ? e(x) : Z(a) ? e(ce, 1) : e(le, -1);
		}), T(oe), T(p), T(n), T(t), bn(() => {
			g.disabled = Z(c), vr(y, Z(c) ? "Saving..." : "Save Configuration");
		}), Rr(s, () => Z(r), (e) => P(r, e)), Rr(f, () => Z(i), (e) => P(i, e)), ir("click", g, te), $(e, t);
	};
	return Or(me, (e) => {
		Z(s) ? e(he) : Z(p) || e(ge, 1);
	}), T(b), bn(() => vr(pe, Z(p) ? "Expand" : "Collapse")), ir("click", fe, () => P(p, !Z(p))), $(e, b), Je(y);
}
customElements.define("plex-dashboard-card", Zr(di, { apiBase: {} }, [], [], { mode: "open" }));
export { di as default };

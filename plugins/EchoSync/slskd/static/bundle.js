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
function _(e) {
	return e();
}
function te(e) {
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
var y = 1024, b = 2048, x = 4096, ne = 8192, S = 16384, re = 32768, ie = 1 << 25, ae = 65536, oe = 1 << 19, se = 1 << 20, ce = 1 << 21, le = 1 << 22, C = 1 << 23, ue = Symbol("$state"), de = Symbol("component"), fe = Symbol("legacy props"), pe = Symbol(""), me = Symbol("attributes"), he = Symbol("class"), ge = Symbol("style"), _e = Symbol("text"), ve = Symbol("form reset"), ye = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), be = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function xe() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Se(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Ce() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
// node_modules/svelte/src/internal/client/dom/hydration.js
var w = !1;
function we(e) {
	w = e;
}
var T;
function E(e) {
	if (e === null) throw Se(), n;
	return T = e;
}
function Te() {
	return E(/* @__PURE__ */ $t(T));
}
function D(e) {
	if (w) {
		if (/* @__PURE__ */ $t(T) !== null) throw Se(), n;
		T = e;
	}
}
function Ee(e = 1) {
	if (w) {
		for (var t = e, n = T; t--;) n = /* @__PURE__ */ $t(n);
		T = n;
	}
}
function De(e = !0) {
	for (var t = 0, n = T;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r.startsWith("[?") || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ $t(n);
		e && n.remove(), n = i;
	}
}
function Oe(e) {
	if (!e || e.nodeType !== 8) throw Se(), n;
	return e.data;
}
// node_modules/svelte/src/internal/client/reactivity/equality.js
function ke(e) {
	return e === this.v;
}
function Ae(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function je(e) {
	return !Ae(e, this.v);
}
function Me(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
// node_modules/svelte/src/internal/client/errors.js
function Ne() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Pe(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Fe() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Ie(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Le() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Re() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function ze(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Be() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Ve() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function He() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Ue() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
// node_modules/svelte/src/internal/client/context.js
var O = null;
function We(e) {
	O = e;
}
function Ge(t, n = !1, r) {
	O = {
		p: O,
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
function Ke(e) {
	var t = O, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) fn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, O = t.p, qe(e);
}
function qe(e = {}) {
	return u(e, de, { value: !0 }), e;
}
function Je() {
	return !e || O !== null && O.l === null;
}
// node_modules/svelte/src/internal/client/dom/task.js
var Ye = [];
function Xe() {
	var e = Ye;
	Ye = [], te(e);
}
function Ze(e) {
	if (Ye.length === 0 && !St) {
		var t = Ye;
		queueMicrotask(() => {
			t === Ye && Xe();
		});
	}
	Ye.push(e);
}
function Qe() {
	for (; Ye.length > 0;) Xe();
}
// node_modules/svelte/src/internal/client/reactivity/status.js
var $e = ~(b | x | y);
function k(e, t) {
	e.f = e.f & $e | t;
}
function et(e) {
	e.f & 512 || e.deps === null ? k(e, y) : k(e, x);
}
// node_modules/svelte/src/internal/client/reactivity/utils.js
function tt(e, t) {
	e.f & 2048 ? t.set(e, b) : e.f & 4096 && t.get(e) !== 2048 && t.set(e, x), k(e, y);
}
// node_modules/svelte/src/internal/client/dom/elements/misc.js
var nt = !1;
function rt() {
	nt || (nt = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ve]?.();
		});
	}, { capture: !0 }));
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function it(e) {
	var t = H, n = G;
	W(null), K(null);
	try {
		return e();
	} finally {
		W(t), K(n);
	}
}
function at(e, t, n, r = n) {
	e.addEventListener(t, () => it(n));
	let i = e[ve];
	e[ve] = i ? () => {
		i(), r(!0);
	} : () => r(!0), rt();
}
// node_modules/svelte/src/internal/client/reactivity/async.js
function ot(e, t, n, r) {
	let i = Je() ? ut : pt;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = G, c = st(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				z(e, s);
			}
			ct();
		}
	}
	var d = lt();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ ft(e))).then(u).catch((e) => z(e, s)).finally(d);
	}
	l ? l.then(() => {
		s.f & 16384 ? d() : (c(), f(), ct());
	}) : f();
}
function st() {
	var e = G, t = H, n = O, r = A;
	return function(i = !0) {
		K(e), W(t), We(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function ct(e = !0) {
	K(null), W(null), We(null), e && A?.deactivate();
}
function lt() {
	var e = G, t = e.b, n = A, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function ut(e) {
	var t = 2 | b;
	return G !== null && (G.f |= oe), {
		ctx: O,
		deps: null,
		effects: null,
		equals: ke,
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
var dt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function ft(e, t, n) {
	let i = G;
	i === null && Ne();
	var a = void 0, o = Lt(r), s = !H, c = /* @__PURE__ */ new Set();
	return _n(() => {
		var t = G, n = v();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== ye && n.reject(e);
			}).finally(ct);
		} catch (e) {
			n.reject(e), ct();
		}
		var r = A;
		if (s) {
			if (t.f & 32768) var l = lt();
			if (i.b?.is_rendered()) r.async_deriveds.get(t)?.reject(dt);
			else for (let e of c.values()) e.reject(dt);
			c.add(n), r.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== dt && (r.activate(), t ? (o.f |= C, Vt(o, t)) : (o.f & 8388608 && (o.f ^= C), Vt(o, e)), r.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), un(() => {
		for (let e of c) e.reject(dt);
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
function pt(e) {
	let t = /* @__PURE__ */ ut(e);
	return t.equals = je, t;
}
function mt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function ht(e) {
	var t, n = G, i = e.parent;
	if (!Nn && i !== null && e.v !== r && i.f & 24576) return xe(), e.v;
	K(i);
	try {
		mt(e), t = Wn(e);
	} finally {
		K(n);
	}
	return t;
}
function gt(e) {
	var t = ht(e);
	!e.equals(t) && (e.wv = Vn(), (!A?.is_fork || e.deps === null) && (A === null ? e.v = t : (A.capture(e, t, !0), bt?.capture(e, t, !0)), e.deps === null)) ? k(e, y) : Nn || (j === null ? et(e) : (ln() || A?.is_fork) && j.set(e, t));
}
function _t(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && it(() => {
		t.ac.abort(ye), t.ac = null;
	}), t.fn !== null && (t.teardown = g), qn(t, 0), Cn(t));
}
function vt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && Jn(t);
}
// node_modules/svelte/src/internal/client/reactivity/batch.js
var yt = null, A = null, bt = null, j = null, xt = null, St = !1, Ct = !1, wt = null, Tt = null, Et = 0, Dt = 1, Ot = class e {
	id = Dt++;
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
		yt === null ? yt = this : (yt.next = this, this.prev = yt), yt = this;
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
			for (var r of n.d) k(r, b), t(r);
			for (r of n.m) k(r, x), t(r);
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
					t.f ^= y;
				}
			}
			n || e.push(t);
		}
		return this.#a = [], e;
	}
	#m() {
		this.started = !0;
		for (let [e, t] of this.#s) k(e, t), this.schedule(e);
		this.apply();
		for (var t = wt = [], n = [], r = Tt = []; this.#a.length > 0;) {
			Et++ > 1e3 && (this.#b(), At());
			for (let e of this.#p()) try {
				this.#h(e, t, n);
			} catch (t) {
				throw Pt(e), this.#d() || this.discard(), t;
			}
			if (this.#a.length > 0) {
				for (let e of n) this.#a.push(e);
				for (let e of t) this.#a.push(e);
				n.length = 0, t.length = 0;
			}
		}
		if (A = null, r.length > 0) {
			var i = e.ensure();
			for (let e of r) i.schedule(e);
		}
		if (wt = null, Tt = null, this.#d()) {
			this.#y(n), this.#y(t);
			for (let [e, t] of this.#c) Nt(e, t);
			r.length > 0 && A.#m();
			return;
		}
		let a = this.#g();
		if (a) this.#y(n), this.#y(t), a.#v(this);
		else {
			this.#s.clear();
			for (let e of this.#e) e(this);
			this.#e.clear(), bt = this, jt(n), jt(t), bt = null, this.#i?.resolve();
			var o = A;
			this.#n === 0 && (this.#a.length === 0 || o !== null) && this.#b(), o !== null && (N.clear(), o.#m());
		}
	}
	#h(e, t, n) {
		e.f ^= y;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = !!(i & 96);
			if (!(a && i & 1024 || i & 8192 || this.#c.has(r)) && r.fn !== null) {
				a ? r.f ^= y : i & 4 ? t.push(r) : Hn(r) && (i & 16 && this.add_dirty_reaction(r, x), Jn(r));
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
					r & 4194320 && !this.async_deriveds.has(i) && (this.#s.delete(i), k(i, b), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#b(), A = this, this.#m();
	}
	#y(e) {
		for (var t = 0; t < e.length; t += 1) tt(e[t], this.#s);
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
			Ct = !0, A = this, this.#m();
		} finally {
			Et = 0, xt = null, wt = null, Tt = null, Ct = !1, A = null, j = null, N.clear();
		}
	}
	discard() {
		for (let e of this.#t) e(this);
		this.#t.clear();
		for (let e of this.async_deriveds.values()) e.reject(dt);
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
		this.#u || (this.#u = !0, Ze(() => {
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
		return (this.#i ??= v()).promise;
	}
	static ensure() {
		if (A === null) {
			let t = A = new e();
			!Ct && !St && Ze(() => {
				t.started || t.flush();
			});
		}
		return A;
	}
	apply() {
		j = null;
	}
	schedule(e) {
		xt = e, e.b?.is_pending && e.f & 16777228 && !(e.f & 32768) ? e.b.defer_effect(e) : this.#a.push(e);
	}
	#b() {
		if (this.linked) {
			var e = this.prev, t = this.next;
			e === null || (e.next = t), t === null ? yt = e : t.prev = e, this.linked = !1;
		}
	}
};
function kt(e) {
	var t = St, n = bt;
	bt = null, St = !0;
	try {
		var r;
		for (e && (kt(), r = e());;) {
			if (Qe(), A === null) return r;
			A.flush();
		}
	} finally {
		St = t, bt = n;
	}
}
function At() {
	try {
		Le();
	} catch (e) {
		z(e, xt);
	}
}
var M = null;
function jt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Hn(r) && (M = /* @__PURE__ */ new Set(), Jn(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && En(r), M?.size > 0)) {
				N.clear();
				for (let e of M) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) M.has(n) && (M.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || Jn(n);
					}
				}
				M.clear();
			}
		}
		M = null;
	}
}
function Mt(e) {
	A.schedule(e);
}
function Nt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), k(e, y);
		for (var n = e.first; n !== null;) Nt(n, t), n = n.next;
	}
}
function Pt(e) {
	k(e, y);
	for (var t = e.first; t !== null;) Pt(t), t = t.next;
}
// node_modules/svelte/src/internal/client/reactivity/sources.js
var Ft = /* @__PURE__ */ new Set(), N = /* @__PURE__ */ new Map(), It = !1;
function Lt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: ke,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Rt(e, t) {
	let n = Lt(e, t);
	return Fn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function P(t, n = !1, r = !0) {
	let i = Lt(t);
	return n || (i.equals = je), e && r && O !== null && O.l !== null && (O.l.s ??= []).push(i), i;
}
function F(e, t, n = !1) {
	return H !== null && (!U || H.f & 131072) && Je() && H.f & 4325394 && (q === null || !q.has(e)) && He(), Vt(e, n ? Gt(t) : t, Tt);
}
var zt = null, Bt = 0;
function Vt(e, t, n = null) {
	if (!e.equals(t)) {
		Nn ? N.set(e, t) : N.has(e) || N.set(e, e.v);
		var r = Ot.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && ht(t), j === null && et(t);
		}
		e.wv = Vn(), zt = null, Bt = 0, Wt(e, b, n), zt = null, Je() && G !== null && G.f & 1024 && !(G.f & 96) && (X === null ? In([e]) : X.push(e)), !r.is_fork && Ft.size > 0 && !It && Ht();
	}
	return t;
}
function Ht() {
	It = !1;
	for (let e of Ft) {
		e.f & 1024 && k(e, x);
		let t;
		try {
			t = Hn(e);
		} catch {
			t = !0;
		}
		t && Jn(e);
	}
	Ft.clear();
}
function Ut(e) {
	F(e, e.v + 1);
}
function Wt(e, t, n) {
	var r = e.reactions;
	if (r !== null) {
		var i = Je(), a = r.length;
		if (Bt += a, Bt > 1e5 && zt === null && (zt = /* @__PURE__ */ new Set()), zt !== null) {
			if (zt.has(e)) return;
			zt.add(e);
		}
		for (var o = 0; o < a; o++) {
			var s = r[o], c = s.f;
			if (i || s !== G) {
				var l = (c & b) === 0;
				if (l && k(s, t), c & 131072) Ft.add(s);
				else if (c & 2) {
					var u = s;
					j?.delete(u), Wt(u, x, n);
				} else if (l) {
					var d = s;
					c & 16 && M !== null && M.add(d), n === null ? Mt(d) : n.push(d);
				}
			}
		}
	}
}
function Gt(e) {
	if (typeof e != "object" || !e || ue in e || de in e) return e;
	let t = h(e);
	if (t !== p && t !== m) return e;
	var n = /* @__PURE__ */ new Map(), i = a(e), o = /* @__PURE__ */ Rt(0), s = null, c = zn, l = (e) => {
		if (zn === c) return e();
		var t = H, n = zn;
		W(null), Bn(c);
		var r = e();
		return W(t), Bn(n), r;
	};
	return i && n.set("length", /* @__PURE__ */ Rt(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			"value" in r && r.configurable !== !1 && r.enumerable !== !1 && r.writable !== !1 || Be();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Rt(r.value, s);
				return n.set(t, e), e;
			}) : F(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var i = n.get(t);
			if (i === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Rt(r, s));
					n.set(t, e), Ut(o);
				}
			} else F(i, r), Ut(o);
			return !0;
		},
		get(t, i, a) {
			if (i === ue) return e;
			var o = n.get(i), c = i in t;
			if (o === void 0 && (!c || d(t, i)?.writable) && (o = l(() => /* @__PURE__ */ Rt(Gt(c ? t[i] : r), s)), n.set(i, o)), o !== void 0) {
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
			if (t === ue) return !0;
			var i = n.get(t), a = i !== void 0 && i.v !== r || Reflect.has(e, t);
			return (i !== void 0 || (G !== null || H !== null) && (!a || d(e, t)?.writable)) && (i === void 0 && (i = l(() => /* @__PURE__ */ Rt(a ? Gt(e[t]) : r, s)), n.set(t, i)), Z(i) === r) ? !1 : a;
		},
		set(e, t, a, c) {
			var u = n.get(t), f = t in e;
			if (i && t === "length") for (var p = a; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Rt(r, s)), n.set(p + "", m)) : F(m, r);
			}
			if (u === void 0) (!f || d(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Rt(void 0, s)), F(u, Gt(a)), n.set(t, u));
			else {
				f = u.v !== r;
				var h = l(() => Gt(a));
				F(u, h);
			}
			var ee = Reflect.getOwnPropertyDescriptor(e, t);
			if (ee?.set && ee.set.call(c, a), !f) {
				if (i && typeof t == "string") {
					var g = n.get("length"), _ = Number(t);
					Number.isInteger(_) && _ >= g.v && F(g, _ + 1);
				}
				Ut(o);
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
			Ve();
		}
	});
}
var Kt, qt, Jt, Yt;
function Xt() {
	if (Kt === void 0) {
		Kt = window, qt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Jt = d(t, "firstChild").get, Yt = d(t, "nextSibling").get, ee(e) && (e[he] = void 0, e[me] = null, e[ge] = void 0, e.__e = void 0), ee(n) && (n[_e] = void 0);
	}
}
function Zt(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function Qt(e) {
	return Jt.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function $t(e) {
	return Yt.call(e);
}
function I(e, t) {
	if (!w) return /* @__PURE__ */ Qt(e);
	var n = /* @__PURE__ */ Qt(T);
	if (n === null) n = T.appendChild(Zt());
	else if (t && n.nodeType !== 3) {
		var r = Zt();
		return n?.before(r), E(r), r;
	}
	return t && an(n), E(n), n;
}
function en(e, t = !1) {
	if (!w) {
		var n = /* @__PURE__ */ Qt(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ $t(n) : n;
	}
	if (t) {
		if (T?.nodeType !== 3) {
			var r = Zt();
			return T?.before(r), E(r), r;
		}
		an(T);
	}
	return T;
}
function L(e, t = !1) {
	if (!w) return /* @__PURE__ */ Qt(e);
	var n = I(e, t);
	return D(e), n;
}
function R(e, t = 1, n = !1) {
	let r = w ? T : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ $t(r);
	if (!w) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = Zt();
			return r === null ? i?.after(a) : r.before(a), E(a), a;
		}
		an(r);
	}
	return E(r), r;
}
function tn(e) {
	e.textContent = "";
}
function nn() {
	return !1;
}
function rn(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function an(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
function on(e) {
	var t = G;
	if (t === null) return H.f |= C, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	z(e, t);
}
function z(e, t) {
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
function sn(e) {
	G === null && (H === null && Ie(e), Fe()), Nn && Pe(e);
}
function cn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function B(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= ne);
	var r = {
		ctx: O,
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
	A?.register_created_effect(r);
	var i = r;
	if (e & 4) wt === null ? Ot.ensure().schedule(r) : wt.push(r);
	else if (t !== null) {
		try {
			Jn(r);
		} catch (e) {
			throw V(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= ae));
	}
	if (i !== null && (i.parent = n, n !== null && cn(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function ln() {
	return H !== null && !U;
}
function un(e) {
	let t = B(8, null);
	return k(t, y), t.teardown = e, t;
}
function dn(e) {
	sn("$effect");
	var t = G.f;
	if (!H && t & 32 && O !== null && !O.i) {
		var n = O;
		(n.e ??= []).push(e);
	} else return fn(e);
}
function fn(e) {
	return B(4 | se, e);
}
function pn(e) {
	return sn("$effect.pre"), B(8 | se, e);
}
function mn(e) {
	Ot.ensure();
	let t = B(64 | oe, e);
	return () => {
		V(t);
	};
}
function hn(e) {
	Ot.ensure();
	let t = B(64 | oe, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Dn(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function gn(e) {
	return B(4, e);
}
function _n(e) {
	return B(le | oe, e);
}
function vn(e, t = 0) {
	return B(8 | t, e);
}
function yn(e, t = [], n = [], r = []) {
	ot(r, t, n, (t) => {
		B(8, () => {
			e(...t.map(Z));
		});
	});
}
function bn(e, t = 0) {
	return B(16 | t, e);
}
function xn(e) {
	return B(32 | oe, e);
}
function Sn(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = Nn, r = H;
		Pn(!0), W(null);
		try {
			t.call(null);
		} catch (t) {
			z(t, e.parent);
		} finally {
			Pn(n), W(r);
		}
	}
}
function Cn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && it(() => {
			e.abort(ye);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function wn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Tn(e.nodes.start, e.nodes.end), n = !0), e.f |= ie, Cn(e, t && !n), qn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Sn(e), e.f ^= ie, e.f |= S;
	var i = e.parent;
	i !== null && i.first !== null && En(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Tn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ $t(e);
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
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function On(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ne;
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
		e.f ^= ne, e.f & 1024 || (k(e, b), Ot.ensure().schedule(e));
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
		var i = n === r ? null : /* @__PURE__ */ $t(n);
		t.append(n), n = i;
	}
}
// node_modules/svelte/src/internal/client/legacy.js
var Mn = null, Nn = !1;
function Pn(e) {
	Nn = e;
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
function Fn(e) {
	H !== null && (H.f & 2097152 || H.f & 2) && (q ??= /* @__PURE__ */ new Set()).add(e);
}
var J = null, Y = 0, X = null;
function In(e) {
	X = e;
}
var Ln = 1, Rn = 0, zn = Rn;
function Bn(e) {
	zn = e;
}
function Vn() {
	return ++Ln;
}
function Hn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Hn(a) && gt(a), a.wv > e.wv) return !0;
		}
		t & 512 && j === null && k(e, y);
	}
	return !1;
}
function Un(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(q !== null && q.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? Un(a, t, !1) : t === a && (n ? k(a, b) : a.f & 1024 && k(a, x), Mt(a));
	}
}
function Wn(e) {
	var t = J, n = Y, r = X, i = H, a = q, o = O, s = U, c = zn, l = e.f;
	J = null, Y = 0, X = null, H = l & 96 ? null : e, q = null, We(e.ctx), U = !1, zn = ++Rn, e.ac !== null && (it(() => {
		e.ac.abort(ye);
	}), e.ac = null);
	try {
		e.f |= ce;
		var u = e.fn, d = u();
		e.f |= re;
		var f = Gn(e);
		if (Je() && X !== null && !U && f !== null && !(e.f & 6146)) for (var p = 0; p < X.length; p++) Un(X[p], e);
		if (i !== null && i !== e) {
			if (Rn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Rn;
			if (t !== null) for (let e of t) e.rv = Rn;
			X !== null && (r === null ? r = X : r.push(...X));
		}
		return e.f & 8388608 && (e.f ^= C), d;
	} catch (t) {
		return Gn(e), on(t);
	} finally {
		e.f ^= ce, J = t, Y = n, X = r, H = i, q = a, We(o), U = s, zn = c;
	}
}
function Gn(e) {
	var t = e.deps, n = A?.is_fork;
	if (J !== null) {
		var r;
		if (n || qn(e, Y), t !== null && Y > 0) for (t.length = Y + J.length, r = 0; r < J.length; r++) t[Y + r] = J[r];
		else e.deps = t = J;
		if (ln() && e.f & 512) for (r = Y; r < t.length; r++) (t[r].reactions ??= []).push(e);
	} else !n && t !== null && Y < t.length && (qn(e, Y), t.length = Y);
	return t;
}
function Kn(e, t) {
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
		c.f & 512 && (c.f ^= 512), c.v !== r && et(c), c.ac !== null && it(() => {
			c.ac.abort(ye), c.ac = null, k(c, b);
		}), _t(c), qn(c, 0);
	}
}
function qn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Kn(e, n[r]);
}
function Jn(e) {
	var t = e.f;
	if (!(t & 16384)) {
		k(e, y);
		var n = G;
		G = e;
		try {
			t & 16777232 ? wn(e) : Cn(e), Sn(e);
			var r = Wn(e);
			e.teardown = typeof r == "function" ? r : null, e.wv = Ln;
		} finally {
			G = n;
		}
	}
}
async function Yn() {
	await Promise.resolve(), kt();
}
function Z(e) {
	var t = !!(e.f & 2);
	if (Mn?.add(e), H !== null && !U && !(G !== null && G.f & 16384) && (q === null || !q.has(e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < Rn && (e.rv = Rn, J === null && n !== null && n[Y] === e ? Y++ : J === null ? J = [e] : J.push(e));
		else {
			H.deps ??= [], s.call(H.deps, e) || H.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : s.call(r, H) || r.push(H);
		}
	}
	if (Nn && N.has(e)) return N.get(e);
	if (t) {
		var i = e;
		if (Nn) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || Zn(i)) && (a = ht(i)), N.set(i, a), a;
		}
		var o = !(i.f & 512) && !U && H !== null && !!(H.f & 512), c = (i.f & re) === 0;
		Hn(i) && (o && (i.f |= 512), gt(i)), o && !c && (vt(i), Xn(i));
	}
	if (j?.has(e)) return j.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function Xn(e) {
	if (e.f |= 512, e.deps !== null) for (let n of e.deps) {
		var t = n.reactions;
		t === null ? n.reactions = [e] : s.call(t, e) || t.push(e), n.f & 2 && !(n.f & 512) && (vt(n), Xn(n));
	}
}
function Zn(e) {
	if (e.v === r) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (N.has(t) || t.f & 2 && Zn(t)) return !0;
	return !1;
}
function Qn(e) {
	var t = U;
	try {
		return U = !0, e();
	} finally {
		U = t;
	}
}
function $n(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (ue in e) er(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && ue in n && er(n);
		}
	}
}
function er(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			er(e[n], t);
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
var tr = Symbol("events"), nr = /* @__PURE__ */ new Set(), rr = /* @__PURE__ */ new Set();
function ir(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || cr.call(t, e), !e.cancelBubble) return it(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? (i.__removed = !1, Ze(() => {
		i.__removed || t.addEventListener(e, i, r);
	})) : t.addEventListener(e, i, r), i;
}
function ar(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = ir(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && un(() => {
		o.__removed = !0, t.removeEventListener(e, o, a);
	});
}
var or = null, sr = !1;
function cr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	or = e, sr || (sr = !0, setTimeout(() => {
		sr = !1, or = null;
	}));
	var o = 0, s = or === e && e[tr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[tr] = t;
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
					var h = a[tr]?.[r];
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
			e[tr] = t, delete e.currentTarget, W(d), K(f);
		}
	}
}
// node_modules/svelte/src/internal/client/dom/reconciler.js
var lr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function ur(e) {
	return lr?.createHTML(e) ?? e;
}
function dr(e) {
	var t = rn("template");
	return t.innerHTML = ur(e.replaceAll("<!>", "<!---->")), t.content;
}
// node_modules/svelte/src/internal/client/dom/template.js
function fr(e, t) {
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
		if (w) return fr(T, null), T;
		i === void 0 && (i = dr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ Qt(i)));
		var t = r || qt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ Qt(t), s = t.lastChild;
			fr(o, s);
		} else fr(t, t);
		return t;
	};
}
function $(e, t) {
	if (w) {
		var n = G;
		n.f & 32768 && n.nodes.end !== null || (n.nodes.end = T), Te();
	} else e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var pr = ["touchstart", "touchmove"];
function mr(e) {
	return pr.includes(e);
}
// node_modules/svelte/src/reactivity/create-subscriber.js
function hr(e) {
	let t = 0, n = Lt(0), r;
	return () => {
		ln() && (Z(n), vn(() => (t === 0 && (r = Qn(() => e(() => Ut(n)))), t += 1, () => {
			Ze(() => {
				--t, t === 0 && (r?.(), r = void 0, Ut(n));
			});
		})));
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var gr = ae | oe;
function _r(e, t, n, r) {
	new vr(e, t, n, r);
}
var vr = class {
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
	#f = /* @__PURE__ */ new Map();
	#p = null;
	#m = hr(() => (this.#p = Lt(this.#l), () => {
		this.#p = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = bn(() => {
			if (w) {
				let e = Oe(this.#t);
				Te();
				let t = e === "[!";
				if (e.startsWith("[?")) {
					let t = JSON.parse(e.slice(2));
					this.#g(t);
				} else t ? this.#y() : this.#h();
			} else this.#b();
		}, gr), w && (this.#e = T);
	}
	#h() {
		try {
			this.#a = xn(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#g(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#_(e);
		Ze(r), t && (this.#s = xn(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#_(e) {
		var t = !1, n = !1;
		let r = () => {
			this.#v() || (t ? Ce() : (t = !0, n && Ue(), this.#s !== null && Dn(this.#s, () => {
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
					z(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#v() {
		return (this.#i.f & (S | ie)) !== 0;
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = xn(() => e(this.#e)), Ze(() => {
			if (!this.#v()) {
				var e = this.#c = document.createDocumentFragment(), t = Zt(), n = !1;
				e.append(t), this.#a = this.#S(() => {
					try {
						return xn(() => this.#r(t));
					} catch (e) {
						try {
							this.error(e), n = !0;
						} catch (e) {
							z(e, this.#i.parent);
						}
						return null;
					}
				}), this.#a === null ? (this.#c = null, n && this.#x(A)) : this.#u === 0 && (this.#e.before(e), this.#c = null, Dn(this.#o, () => {
					this.#o = null;
				}), this.#x(A));
			}
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = xn(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				jn(this.#a, e);
				let t = this.#n.pending;
				this.#o = xn(() => t(this.#e));
			} else this.#x(A);
		} catch (e) {
			this.error(e);
		}
	}
	#x(e) {
		this.is_pending = !1, e.transfer_reactions(this.#f);
	}
	defer_effect(e) {
		tt(e, this.#f);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#S(e) {
		var t = G, n = H, r = O;
		K(this.#i), W(this.#i), We(this.#i.ctx);
		try {
			return Ot.ensure(), e();
		} finally {
			K(t), W(n), We(r);
		}
	}
	#C(e, t) {
		this.has_pending_snippet() ? (this.#u += e, this.#u === 0 && (this.#x(t), this.#o && Dn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null))) : this.parent && this.parent.#C(e, t);
	}
	update_pending_count(e, t) {
		this.#C(e, t), this.#l += e, !this.#p || this.#d || (this.#d = !0, Ze(() => {
			this.#d = !1, this.#p && Vt(this.#p, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#m(), Z(this.#p);
	}
	error(e) {
		if (e === n || !this.#n.onerror && !this.#n.failed) throw e;
		A?.is_fork ? (this.#a && A.skip_effect(this.#a), this.#o && A.skip_effect(this.#o), this.#s && A.skip_effect(this.#s), A.oncommit(() => {
			this.#v() || this.#w(e);
		})) : this.#w(e);
	}
	#w(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), w && (E(this.#t), Ee(), E(De()));
		let t = this.#n.failed, n = (e) => {
			if (this.#v()) return;
			let { reset: n, invoke_onerror: r } = this.#_(e);
			r(), t && !this.#v() && (this.#s = this.#S(() => {
				try {
					return xn(() => {
						var r = G;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return z(e, this.#i.parent), null;
				}
			}));
		};
		Ze(() => {
			if (!this.#v()) {
				var t;
				try {
					t = this.transform_error(e);
				} catch (e) {
					z(e, this.#i && this.#i.parent);
					return;
				}
				typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => z(e, this.#i && this.#i.parent)) : n(t);
			}
		});
	}
};
function yr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[_e] ??= e.nodeValue) && (e[_e] = n, e.nodeValue = `${n}`);
}
function br(e, t) {
	return Cr(e, t);
}
function xr(e, t) {
	Xt(), t.intro = t.intro ?? !1;
	let r = t.target, i = w, a = T;
	try {
		for (var o = /* @__PURE__ */ Qt(r); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ $t(o);
		if (!o) throw n;
		we(!0), E(o);
		let i = Cr(e, {
			...t,
			anchor: o
		});
		return we(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== n && console.warn("Failed to hydrate: ", i), t.recover === !1 && Re(), Xt(), tn(r), we(!1), br(e, t);
	} finally {
		we(i), E(a);
	}
}
var Sr = /* @__PURE__ */ new Map();
function Cr(e, { target: t, anchor: r, props: i = {}, events: a, context: o, intro: s = !0, transformError: l }) {
	Xt();
	var u = void 0, d = hn(() => {
		var s = r ?? t.appendChild(Zt());
		_r(s, { pending: () => {} }, (t) => {
			Ge({});
			var r = O;
			if (o && (r.c = o), a && (i.$$events = a), w && fr(t, null), u = e(t, i) || qe(), w && (G.nodes.end = T, T === null || T.nodeType !== 8 || T.data !== "]")) throw Se(), n;
			Ke();
		}, l);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = mr(r);
					for (let e of [t, document]) {
						var a = Sr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), Sr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, cr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(c(nr)), rr.add(f), () => {
			for (var e of d) for (let r of [t, document]) {
				var n = Sr.get(r), i = n.get(e);
				--i == 0 ? (r.removeEventListener(e, cr), n.delete(e), n.size === 0 && Sr.delete(r)) : n.set(e, i);
			}
			rr.delete(f), s !== r && s.parentNode?.removeChild(s);
		};
	});
	return wr.set(u, d), u;
}
var wr = /* @__PURE__ */ new WeakMap();
function Tr(e, t) {
	let n = wr.get(e);
	return n ? (wr.delete(e), n(t)) : Promise.resolve();
}
// node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Er = class {
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
				r && (V(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						jn(r, t), t.append(Zt()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Dn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = A, r = nn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = document.createDocumentFragment(), a = Zt();
				i.append(a), this.#n.set(e, {
					effect: xn(() => t(a)),
					fragment: i
				});
			} else this.#t.set(e, xn(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else w && (this.anchor = T), this.#a(n);
	}
};
function Dr(t) {
	O === null && Me("onMount"), e && O.l !== null ? Or(O).m.push(t) : dn(() => {
		let e = Qn(t);
		if (typeof e == "function") return e;
	});
}
function Or(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/if.js
function kr(e, t, n = !1) {
	var r;
	w && (r = T, Te());
	var i = new Er(e), a = n ? ae : 0;
	function o(e, t) {
		if (w) {
			var n = Oe(r);
			if (e !== parseInt(n.substring(1))) {
				var a = De();
				E(a), i.anchor = a, we(!1), i.ensure(e, t), we(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	bn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
// node_modules/svelte/src/internal/client/dom/css.js
function Ar(e, t) {
	gn(() => {
		e = G?.parent?.nodes?.start ?? e;
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = rn("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
// node_modules/svelte/src/internal/shared/attributes.js
var jr = [..." 	\n\r\f\xA0\v﻿"];
function Mr(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || jr.includes(r[o - 1])) && (s === r.length || jr.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
// node_modules/svelte/src/internal/client/dom/elements/class.js
function Nr(e, t, n, r, i, a) {
	var o = e[he];
	if (w || o !== n || o === void 0) {
		var s = Mr(n, r, a);
		w && s === e.getAttribute("class") || (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e[he] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
// node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Pr = Symbol("is custom element"), Fr = Symbol("is html"), Ir = be ? "link" : "LINK", Lr = be ? "progress" : "PROGRESS";
function Rr(e) {
	if (w) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Br(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Br(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ve] = n, Ze(n), rt();
	}
}
function zr(e, t) {
	var n = Vr(e);
	n.value !== (n.value = t ?? void 0) && (e.value !== t || t === 0 && e.nodeName === Lr) && (e.value = t ?? "");
}
function Br(e, t, n, r) {
	var i = Vr(e);
	if (!(w && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Ir))) {
		var a = i[t];
		a !== (i[t] = n) && (t === "loading" && (e[pe] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Ur(e).has(t) ? e[t] = n : (!w || typeof n != "number" && typeof n != "boolean" || a !== String(n)) && e.setAttribute(t, n));
	}
}
function Vr(e) {
	return e[me] ??= {
		[Pr]: e.nodeName.includes("-"),
		[Fr]: e.namespaceURI === i
	};
}
var Hr = /* @__PURE__ */ new Map();
function Ur(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Hr.get(t);
	if (n) return n;
	Hr.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = f(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.add(o);
		i = h(i);
	}
	return n;
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Wr(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	at(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = Gr(e) ? Kr(a) : a, n(a), A !== null && r.add(A), await Yn(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (w && e.defaultValue !== e.value || Qn(t) == null && e.value) && (n(Gr(e) ? Kr(e.value) : e.value), A !== null && r.add(A)), vn(() => {
		var n = t();
		if (e === document.activeElement) {
			var i = A;
			if (r.has(i)) return;
		}
		Gr(e) && n === Kr(e.value) || (e.type !== "date" || n || e.value) && n !== e.value && (e.value = n ?? "");
	});
}
function Gr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Kr(e) {
	return e === "" ? null : +e;
}
// node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function qr(e = !1) {
	let t = O, n = t.l.u;
	if (!n) return;
	let r = () => $n(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ ut(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Z(i);
	}
	n.b.length && pn(() => {
		Jr(t, r), te(n.b);
	}), dn(() => {
		let e = Qn(() => n.m.map(_));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && dn(() => {
		Jr(t, r), te(n.a);
	});
}
function Jr(e, t) {
	if (e.l.s) for (let t of e.l.s) Z(t);
	t();
}
// node_modules/svelte/src/internal/client/reactivity/store.js
var Yr = !1;
function Xr(e) {
	var t = Yr;
	try {
		return Yr = !1, [e(), Yr];
	} finally {
		Yr = t;
	}
}
// node_modules/svelte/src/internal/client/reactivity/props.js
function Zr(t, n, r, i) {
	var a = !e || !!(r & 2), o = !!(r & 8), s = !!(r & 16), c = i, l = !0, u = void 0, f = () => s && a ? (u ??= /* @__PURE__ */ ut(i), Z(u)) : (l && (l = !1, c = s ? Qn(i) : i), c);
	let p;
	if (o) {
		var m = ue in t || fe in t;
		p = d(t, n)?.set ?? (m && n in t ? (e) => t[n] = e : void 0);
	}
	var h, ee = !1;
	o ? [h, ee] = Xr(() => t[n]) : h = t[n], h === void 0 && i !== void 0 && (h = f(), p && (a && ze(n), p(h)));
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
	var te = !1, v = (r & 1 ? ut : pt)(() => (te = !1, g()));
	o && Z(v);
	var y = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Z(v) : a && o ? Gt(e) : e;
			return F(v, n), te = !0, c !== void 0 && (c = n), e;
		}
		return Nn && te || y.f & 16384 ? v.v : Z(v);
	});
}
// node_modules/svelte/src/legacy/legacy-client.js
function Qr(e) {
	return new $r(e);
}
var $r = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ P(n, !1, !1);
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
				return r === fe || (Z(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return F(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		});
		this.#t = (e.hydrate ? xr : br)(e.component, {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		}), e?.props?.$$host && e.sync !== !1 || kt(), this.#e = r.$$events;
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
			Tr(this.#t);
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
}, ei;
typeof HTMLElement == "function" && (ei = class extends HTMLElement {
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
					let n = rn("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = ni(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = ti(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = Qr({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = mn(() => {
				vn(() => {
					this.$$r = !0;
					for (let e of l(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = ti(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = ti(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
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
function ti(e, t, n, r) {
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
function ni(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function ri(e, t, n, r, i, a) {
	let o = class extends ei {
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
				n = ti(e, n, t), this.$$d[e] = n;
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
// SlskdCard.svelte
var ii = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-11uhbwz\">● Connected</span>"), ai = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-11uhbwz\">⚠ Disconnected</span>"), oi = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-11uhbwz\">● Active</span>"), si = /* @__PURE__ */ Q("<button class=\"btn-ghost small svelte-11uhbwz\">Activate</button>"), ci = /* @__PURE__ */ Q("<div class=\"loading-state svelte-11uhbwz\">Loading...</div>"), li = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-11uhbwz\"> </button>"), ui = /* @__PURE__ */ Q("<div> </div>"), di = /* @__PURE__ */ Q("<div class=\"webhook-details\"><label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Webhook Callback URL</span> <div class=\"copy-input-wrapper svelte-11uhbwz\"><input type=\"text\" readonly=\"\" class=\"input-field readonly svelte-11uhbwz\"/> <button type=\"button\" class=\"btn-copy svelte-11uhbwz\"> </button></div> <span class=\"helper-text svelte-11uhbwz\">Add this URL to your slskd configuration to enable real-time\n              ingestion.</span></label> <div class=\"yaml-block svelte-11uhbwz\"><div class=\"yaml-header svelte-11uhbwz\"><span>slskd.yml Integration Config</span> <button type=\"button\" class=\"btn-ghost small svelte-11uhbwz\"> </button></div> <pre class=\"code-block svelte-11uhbwz\"><code> </code></pre></div> <div class=\"actions-row svelte-11uhbwz\"><button class=\"btn-ghost svelte-11uhbwz\"> </button> <button class=\"btn-ghost svelte-11uhbwz\">Refresh Details</button></div> <!></div>"), fi = /* @__PURE__ */ Q("<div class=\"loading-state svelte-11uhbwz\">Loading webhook configuration...</div>"), pi = /* @__PURE__ */ Q("<div class=\"settings-section svelte-11uhbwz\"><h3 class=\"section-title svelte-11uhbwz\">Server Configuration</h3> <div class=\"form-grid svelte-11uhbwz\"><label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Server URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:5030\" class=\"input-field svelte-11uhbwz\"/> <span class=\"helper-text svelte-11uhbwz\">Enter your slskd server address (include port, default :5030)</span></label> <label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">Server Name (Optional)</span> <input type=\"text\" placeholder=\"My slskd Server\" class=\"input-field svelte-11uhbwz\"/></label> <label class=\"form-field svelte-11uhbwz\"><span class=\"field-label svelte-11uhbwz\">API Key</span> <div class=\"password-wrapper svelte-11uhbwz\"><input placeholder=\"Enter API key\" class=\"input-field svelte-11uhbwz\"/> <button type=\"button\" class=\"toggle-visibility svelte-11uhbwz\" aria-label=\"Toggle API key visibility\"> </button></div> <span class=\"helper-text svelte-11uhbwz\">API key from slskd settings (Options → Security → API Keys)</span></label> <div class=\"actions-row svelte-11uhbwz\"><button class=\"btn-primary svelte-11uhbwz\"> </button> <!></div></div></div> <div class=\"settings-section webhook-section svelte-11uhbwz\"><h3 class=\"section-title svelte-11uhbwz\">Webhooks & Automation</h3> <p class=\"section-description svelte-11uhbwz\">Configure slskd to immediately notify EchoSync upon download completion\n        or failure. This enables real-time tag verification, automatic library\n        admission, and immediate daemon transfer eviction.</p> <!></div>", 1), mi = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-11uhbwz\"><div class=\"card-header svelte-11uhbwz\"><div class=\"header-left svelte-11uhbwz\"><h2 class=\"card-title svelte-11uhbwz\">Slskd</h2> <div class=\"badges svelte-11uhbwz\"><span class=\"type-badge svelte-11uhbwz\">Download Client</span> <!> <!></div></div> <div class=\"header-right svelte-11uhbwz\"><!> <button class=\"btn-ghost svelte-11uhbwz\"> </button></div></div> <!></section>"), hi = {
	hash: "svelte-11uhbwz",
	code: ".plugin-card.svelte-11uhbwz {box-sizing:border-box;background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-11uhbwz {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle, #1e293b);}.header-left.svelte-11uhbwz {display:flex;align-items:center;gap:16px;}.card-title.svelte-11uhbwz {margin:0;font-size:20px;font-weight:700;}.badges.svelte-11uhbwz {display:flex;gap:8px;}.type-badge.svelte-11uhbwz {font-size:10px;padding:2px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);border-radius:4px;font-weight:700;text-transform:uppercase;}.status-badge.svelte-11uhbwz {font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-11uhbwz {background:rgba(16, 185, 129, 0.15);color:#10b981;}.status-badge.warning.svelte-11uhbwz {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-11uhbwz {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.header-right.svelte-11uhbwz {display:flex;gap:8px;}.btn-ghost.svelte-11uhbwz {padding:8px 16px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.small.svelte-11uhbwz {padding:4px 12px;font-size:11px;font-weight:700;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;}.btn-ghost.svelte-11uhbwz:hover {background:var(--bg-surface-elevated);filter:brightness(1.2);}.btn-primary.svelte-11uhbwz {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-11uhbwz:hover {opacity:0.9;}.loading-state.svelte-11uhbwz {padding:24px;text-align:center;color:var(--text-secondary, #94a3b8);}.settings-section.svelte-11uhbwz {margin-top:16px;}.section-title.svelte-11uhbwz {margin:0 0 16px 0;font-size:16px;font-weight:600;}.form-grid.svelte-11uhbwz {display:flex;flex-direction:column;gap:16px;}.form-field.svelte-11uhbwz {display:flex;flex-direction:column;gap:6px;min-width:0;width:100%;box-sizing:border-box;}.field-label.svelte-11uhbwz {font-size:13px;color:var(--text-secondary, #94a3b8);}.input-field.svelte-11uhbwz {box-sizing:border-box;min-width:0;width:100%;padding:10px 14px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);border-radius:8px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.2s;}.input-field.svelte-11uhbwz:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.password-wrapper.svelte-11uhbwz {position:relative;display:flex;align-items:center;min-width:0;width:100%;box-sizing:border-box;}.toggle-visibility.svelte-11uhbwz {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary, #f8fafc);}.helper-text.svelte-11uhbwz {font-size:11px;color:var(--text-secondary, #94a3b8);}.actions-row.svelte-11uhbwz {display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;}.webhook-section.svelte-11uhbwz {border-top:1px solid var(--border-subtle, #1e293b);padding-top:20px;margin-top:24px;}.section-description.svelte-11uhbwz {font-size:13px;color:var(--text-secondary, #94a3b8);margin:-8px 0 16px 0;line-height:1.4;}.copy-input-wrapper.svelte-11uhbwz {display:flex;gap:8px;}.input-field.readonly.svelte-11uhbwz {background:rgba(15, 23, 42, 0.6);color:var(--color-primary, #14b8a6);font-family:monospace;font-size:12px;}.btn-copy.svelte-11uhbwz {padding:0 16px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:12px;cursor:pointer;font-weight:600;transition:all 0.2s;white-space:nowrap;}.btn-copy.svelte-11uhbwz:hover {background:var(--color-primary, #14b8a6);color:#000;}.yaml-block.svelte-11uhbwz {margin-top:12px;background:#090d16;border:1px solid var(--border-subtle, #1e293b);border-radius:8px;overflow:hidden;}.yaml-header.svelte-11uhbwz {display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:rgba(30, 41, 59, 0.4);border-bottom:1px solid var(--border-subtle, #1e293b);font-size:12px;font-weight:600;color:var(--text-secondary, #94a3b8);}.code-block.svelte-11uhbwz {margin:0;padding:12px;font-family:\"JetBrains Mono\", \"Fira Code\", monospace;font-size:12px;color:#38bdf8;overflow-x:auto;white-space:pre;line-height:1.4;}.test-result-banner.svelte-11uhbwz {margin-top:12px;padding:10px 14px;border-radius:8px;font-size:13px;font-weight:500;}.test-result-banner.success.svelte-11uhbwz {background:rgba(16, 185, 129, 0.15);color:#10b981;border:1px solid rgba(16, 185, 129, 0.3);}.test-result-banner.error.svelte-11uhbwz {background:rgba(239, 68, 68, 0.15);color:#ef4444;border:1px solid rgba(239, 68, 68, 0.3);}"
};
function gi(e, t) {
	Ge(t, !1), Ar(e, hi);
	let n = Zr(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(""), i = /* @__PURE__ */ P(""), a = /* @__PURE__ */ P(""), o = /* @__PURE__ */ P(!1), s = /* @__PURE__ */ P(!0), c = /* @__PURE__ */ P(!1), l = /* @__PURE__ */ P(!1), u = /* @__PURE__ */ P(!1), d = /* @__PURE__ */ P(!1), f = /* @__PURE__ */ P(!1), p = !1, m = /* @__PURE__ */ P(!1), h = /* @__PURE__ */ P(null), ee = /* @__PURE__ */ P(!1), g = /* @__PURE__ */ P(!1), _ = /* @__PURE__ */ P(null), te = /* @__PURE__ */ P(!1), v = /* @__PURE__ */ P(!1);
	Dr(async () => {
		await S(), await x(), await y(), F(s, !1);
	});
	async function y() {
		try {
			F(ee, !0);
			let e = await (await fetch(`${n()}/webhooks/info`)).json();
			e && e.endpoint && F(h, e.endpoint);
		} catch (e) {
			console.error("Failed to load webhook info:", e);
		} finally {
			F(ee, !1);
		}
	}
	async function b() {
		try {
			F(g, !0), F(_, null);
			let e = await fetch(`${n()}/webhooks/test`, { method: "POST" }), t = await e.json();
			e.ok && t.success ? F(_, {
				success: !0,
				message: "Ping successful! Webhook gateway received and dispatched event."
			}) : F(_, {
				success: !1,
				message: t.detail || "Ping failed."
			});
		} catch (e) {
			F(_, {
				success: !1,
				message: `Ping failed: ${e.message}`
			});
		} finally {
			F(g, !1);
		}
	}
	async function x() {
		try {
			let e = await (await fetch(`${n()}/download-clients/active`)).json();
			F(m, e.active_client === "slskd");
		} catch (e) {
			console.error("Failed to check active status:", e);
		}
	}
	async function ne() {
		try {
			await fetch(`${n()}/download-clients/activate`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ client: "slskd" })
			}), F(m, !0);
		} catch (e) {
			console.error("Failed to activate client:", e);
		}
	}
	async function S() {
		try {
			let e = await (await fetch(`${n()}/settings`)).json();
			e && (F(r, e.slskd_url || ""), F(a, e.server_name || ""), F(i, e.api_key || ""), F(f, e.has_api_key || !1), F(o, e.configured || !1));
		} catch (e) {
			console.error("Failed to load slskd settings:", e);
		}
	}
	async function re() {
		if (!Z(r).trim()) console.error("Server URL is required");
		else try {
			F(c, !0);
			let e = {
				slskd_url: Z(r),
				server_name: Z(a)
			};
			Z(i) && Z(i) !== "****" && (e.api_key = Z(i)), await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), await S();
		} catch (e) {
			console.error("Failed to save slskd settings:", e);
		} finally {
			F(c, !1);
		}
	}
	async function ie() {
		if (Z(r).trim()) try {
			F(l, !0), (await (await fetch(`${n()}/connection/test`, { method: "POST" })).json())?.success ? (F(o, !0), await S()) : F(o, !1);
		} catch (e) {
			console.error("Failed to test slskd connection:", e), F(o, !1);
		} finally {
			F(l, !1);
		}
	}
	async function ae() {
		let e = !Z(d);
		if (F(d, e), e && Z(f) && Z(i) === "****" && !p) try {
			let e = await (await fetch(`${n()}/settings/key`)).json();
			e && e.api_key ? (F(i, e.api_key), p = !0) : F(d, !1);
		} catch {
			F(d, !1);
		}
		!e && p && (F(i, "****"), p = !1);
	}
	function oe(e, t) {
		navigator?.clipboard && navigator.clipboard.writeText(e).then(() => {
			t === "yaml" ? (F(te, !0), setTimeout(() => F(te, !1), 2e3)) : (F(v, !0), setTimeout(() => F(v, !1), 2e3));
		});
	}
	var se = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), kt();
		}
	};
	qr();
	var ce = mi(), le = I(ce), C = I(le), ue = R(I(C), 2), de = R(I(ue), 2), fe = (e) => {
		$(e, ii());
	}, pe = (e) => {
		$(e, ai());
	};
	kr(de, (e) => {
		Z(o) ? e(fe) : Z(r) && e(pe, 1);
	});
	var me = R(de, 2), he = (e) => {
		$(e, oi());
	};
	kr(me, (e) => {
		Z(m) && e(he);
	}), D(ue), D(C);
	var ge = R(C, 2), _e = I(ge), ve = (e) => {
		var t = si();
		ar("click", t, ne), $(e, t);
	};
	kr(_e, (e) => {
		!Z(m) && Z(o) && e(ve);
	});
	var ye = R(_e, 2), be = L(ye, !0);
	D(ge), D(le);
	var xe = R(le, 2), Se = (e) => {
		$(e, ci());
	}, Ce = (e) => {
		var t = pi(), n = en(t), o = R(I(n), 2), s = I(o), u = R(I(s), 2);
		Rr(u), Ee(2), D(s);
		var p = R(s, 2), m = R(I(p), 2);
		Rr(m), D(p);
		var x = R(p, 2), ne = R(I(x), 2), S = I(ne);
		Rr(S);
		var se = R(S, 2), ce = L(se, !0);
		D(ne), Ee(2), D(x);
		var le = R(x, 2), C = I(le), ue = L(C, !0), de = R(C, 2), fe = (e) => {
			var t = li(), n = L(t, !0);
			yn(() => {
				t.disabled = Z(l), yr(n, Z(l) ? "Testing..." : "Test Connection");
			}), ar("click", t, ie), $(e, t);
		};
		kr(de, (e) => {
			Z(r) && (Z(f) || Z(i)) && e(fe);
		}), D(le), D(o), D(n);
		var pe = R(n, 2), me = R(I(pe), 4), he = (e) => {
			var t = di(), n = I(t), r = R(I(n), 2), i = I(r);
			Rr(i);
			var a = R(i, 2), o = L(a, !0);
			D(r), Ee(2), D(n);
			var s = R(n, 2), c = I(s), l = R(I(c), 2), u = L(l, !0);
			D(c);
			var d = R(c, 2), f = L(I(d), !0);
			D(d), D(s);
			var p = R(s, 2), m = I(p), x = L(m, !0), ne = R(m, 2);
			D(p);
			var S = R(p, 2), re = (e) => {
				var t = ui(), n = L(t, !0);
				yn(() => {
					Nr(t, 1, `test-result-banner ${Z(_), Qn(() => Z(_).success ? "success" : "error") ?? ""}`, "svelte-11uhbwz"), yr(n, (Z(_), Qn(() => Z(_).message)));
				}), $(e, t);
			};
			kr(S, (e) => {
				Z(_) && e(re);
			}), D(t), yn(() => {
				zr(i, (Z(h), Qn(() => `${Z(h).url}${Z(h).secret ? "?secret=" + Z(h).secret : ""}`))), yr(o, Z(v) ? "Copied!" : "Copy"), yr(u, Z(te) ? "Copied!" : "Copy YAML"), yr(f, (Z(h), Qn(() => Z(h).yaml_template))), m.disabled = Z(g), yr(x, Z(g) ? "Pinging Webhook..." : "Test Webhook Ingress"), ne.disabled = Z(ee);
			}), ar("click", a, () => oe(`${Z(h).url}${Z(h).secret ? "?secret=" + Z(h).secret : ""}`, "url")), ar("click", l, () => oe(Z(h).yaml_template, "yaml")), ar("click", m, b), ar("click", ne, y), $(e, t);
		}, ge = (e) => {
			$(e, fi());
		};
		kr(me, (e) => {
			Z(h) ? e(he) : e(ge, -1);
		}), D(pe), yn(() => {
			Br(S, "type", Z(d) ? "text" : "password"), yr(ce, Z(d) ? "🙈" : "👁️"), C.disabled = Z(c), yr(ue, Z(c) ? "Saving..." : "Save Settings");
		}), Wr(u, () => Z(r), (e) => F(r, e)), Wr(m, () => Z(a), (e) => F(a, e)), Wr(S, () => Z(i), (e) => F(i, e)), ar("click", se, ae), ar("click", C, re), $(e, t);
	};
	return kr(xe, (e) => {
		Z(s) ? e(Se) : Z(u) || e(Ce, 1);
	}), D(ce), yn(() => yr(be, Z(u) ? "Expand" : "Collapse")), ar("click", ye, () => F(u, !Z(u))), $(e, ce), Ke(se);
}
customElements.define("slskd-dashboard-card", ri(gi, { apiBase: {} }, [], [], { mode: "open" }));
export { gi as default };

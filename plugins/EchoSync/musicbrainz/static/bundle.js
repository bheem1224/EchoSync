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
var n = {}, r = Symbol("uninitialized"), i = "http://www.w3.org/1999/xhtml", a = Array.isArray, o = Array.prototype.indexOf, s = Array.prototype.includes, c = Array.from, l = Object.keys, u = Object.defineProperty, d = Object.getOwnPropertyDescriptor, f = Object.getOwnPropertyDescriptors, p = Object.prototype, m = Array.prototype, h = Object.getPrototypeOf, g = Object.isExtensible, _ = () => {};
function v(e) {
	return e();
}
function y(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function b() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var x = 1024, S = 2048, C = 4096, ee = 8192, te = 16384, ne = 32768, re = 1 << 25, w = 65536, T = 1 << 19, ie = 1 << 20, ae = 1 << 25, oe = 1 << 21, se = 1 << 22, ce = 1 << 23, le = Symbol("$state"), ue = Symbol("component"), de = Symbol("legacy props"), fe = Symbol(""), pe = Symbol("attributes"), me = Symbol("class"), he = Symbol("style"), ge = Symbol("text"), _e = Symbol("form reset"), ve = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), ye = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function be() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function xe(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Se() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
// node_modules/svelte/src/internal/client/dom/hydration.js
var E = !1;
function Ce(e) {
	E = e;
}
var D;
function O(e) {
	if (e === null) throw xe(), n;
	return D = e;
}
function we() {
	return O(/* @__PURE__ */ en(D));
}
function k(e) {
	if (E) {
		if (/* @__PURE__ */ en(D) !== null) throw xe(), n;
		D = e;
	}
}
function Te(e = 1) {
	if (E) {
		for (var t = e, n = D; t--;) n = /* @__PURE__ */ en(n);
		D = n;
	}
}
function Ee(e = !0) {
	for (var t = 0, n = D;;) {
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
function De(e) {
	if (!e || e.nodeType !== 8) throw xe(), n;
	return e.data;
}
// node_modules/svelte/src/internal/client/reactivity/equality.js
function Oe(e) {
	return e === this.v;
}
function ke(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Ae(e) {
	return !ke(e, this.v);
}
function je(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
// node_modules/svelte/src/internal/client/errors.js
function Me() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Ne(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
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
var A = null;
function We(e) {
	A = e;
}
function Ge(t, n = !1, r) {
	A = {
		p: A,
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
function Ke(e) {
	var t = A, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) hn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, A = t.p, qe(e);
}
function qe(e = {}) {
	return u(e, ue, { value: !0 }), e;
}
function Je() {
	return !e || A !== null && A.l === null;
}
// node_modules/svelte/src/internal/client/dom/task.js
var Ye = [];
function Xe() {
	var e = Ye;
	Ye = [], y(e);
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
var $e = ~(S | C | x);
function j(e, t) {
	e.f = e.f & $e | t;
}
function et(e) {
	e.f & 512 || e.deps === null ? j(e, x) : j(e, C);
}
// node_modules/svelte/src/internal/client/reactivity/utils.js
function tt(e, t) {
	e.f & 2048 ? t.set(e, S) : e.f & 4096 && t.get(e) !== 2048 && t.set(e, C), j(e, x);
}
// node_modules/svelte/src/internal/client/dom/elements/misc.js
var nt = !1;
function rt() {
	nt || (nt = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[_e]?.();
		});
	}, { capture: !0 }));
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function it(e) {
	var t = H, n = W;
	U(null), Rn(null);
	try {
		return e();
	} finally {
		U(t), Rn(n);
	}
}
function at(e, t, n, r = n) {
	e.addEventListener(t, () => it(n));
	let i = e[_e];
	e[_e] = i ? () => {
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
	var s = W, c = st(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				ln(e, s);
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
		Promise.all(n.map((e) => /* @__PURE__ */ ft(e))).then(u).catch((e) => ln(e, s)).finally(d);
	}
	l ? l.then(() => {
		s.f & 16384 ? d() : (c(), f(), ct());
	}) : f();
}
function st() {
	var e = W, t = H, n = A, r = M;
	return function(i = !0) {
		Rn(e), U(t), We(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function ct(e = !0) {
	Rn(null), U(null), We(null), e && M?.deactivate();
}
function lt() {
	var e = W, t = e.b, n = M, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function ut(e) {
	var t = 2 | S;
	return W !== null && (W.f |= T), {
		ctx: A,
		deps: null,
		effects: null,
		equals: Oe,
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
var dt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function ft(e, t, n) {
	let i = W;
	i === null && Me();
	var a = void 0, o = zt(r), s = !H, c = /* @__PURE__ */ new Set();
	return bn(() => {
		var t = W, n = b();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== ve && n.reject(e);
			}).finally(ct);
		} catch (e) {
			n.reject(e), ct();
		}
		var r = M;
		if (s) {
			if (t.f & 32768) var l = lt();
			if (i.b?.is_rendered()) r.async_deriveds.get(t)?.reject(dt);
			else for (let e of c.values()) e.reject(dt);
			c.add(n), r.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== dt && (r.activate(), t ? (o.f |= ce, Ut(o, t)) : (o.f & 8388608 && (o.f ^= ce), Ut(o, e)), r.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), pn(() => {
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
	return t.equals = Ae, t;
}
function mt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function ht(e) {
	var t, n = W, i = e.parent;
	if (!Fn && i !== null && e.v !== r && i.f & 24576) return be(), e.v;
	Rn(i);
	try {
		mt(e), t = Yn(e);
	} finally {
		Rn(n);
	}
	return t;
}
function gt(e) {
	var t = ht(e);
	!e.equals(t) && (e.wv = Kn(), (!M?.is_fork || e.deps === null) && (M === null ? e.v = t : (M.capture(e, t, !0), bt?.capture(e, t, !0)), e.deps === null)) ? j(e, x) : Fn || (N === null ? et(e) : (fn() || M?.is_fork) && N.set(e, t));
}
function _t(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && it(() => {
		t.ac.abort(ve), t.ac = null;
	}), t.fn !== null && (t.teardown = _), Qn(t, 0), Tn(t));
}
function vt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && $n(t);
}
// node_modules/svelte/src/internal/client/reactivity/batch.js
var yt = null, M = null, bt = null, N = null, xt = null, St = !1, Ct = !1, wt = null, Tt = null, Et = 0, Dt = 1, Ot = class e {
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
			for (var r of n.d) j(r, S), t(r);
			for (r of n.m) j(r, C), t(r);
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
					t.f ^= x;
				}
			}
			n || e.push(t);
		}
		return this.#a = [], e;
	}
	#m() {
		this.started = !0;
		for (let [e, t] of this.#s) j(e, t), this.schedule(e);
		this.apply();
		for (var t = wt = [], n = [], r = Tt = []; this.#a.length > 0;) {
			Et++ > 1e3 && (this.#b(), At());
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
		if (M = null, r.length > 0) {
			var i = e.ensure();
			for (let e of r) i.schedule(e);
		}
		if (wt = null, Tt = null, this.#d()) {
			this.#y(n), this.#y(t);
			for (let [e, t] of this.#c) Pt(e, t);
			r.length > 0 && M.#m();
			return;
		}
		let a = this.#g();
		if (a) this.#y(n), this.#y(t), a.#v(this);
		else {
			this.#s.clear();
			for (let e of this.#e) e(this);
			this.#e.clear(), bt = this, Mt(n), Mt(t), bt = null, this.#i?.resolve();
			var o = M;
			this.#n === 0 && (this.#a.length === 0 || o !== null) && this.#b(), o !== null && (Lt.clear(), o.#m());
		}
	}
	#h(e, t, n) {
		e.f ^= x;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = !!(i & 96);
			if (!(a && i & 1024 || i & 8192 || this.#c.has(r)) && r.fn !== null) {
				a ? r.f ^= x : i & 4 ? t.push(r) : qn(r) && (i & 16 && this.add_dirty_reaction(r, C), $n(r));
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
					r & 4194320 && !this.async_deriveds.has(i) && (this.#s.delete(i), j(i, S), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#b(), M = this, this.#m();
	}
	#y(e) {
		for (var t = 0; t < e.length; t += 1) tt(e[t], this.#s);
	}
	capture(e, t, n = !1) {
		e.v !== r && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), N?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		M = this;
	}
	deactivate() {
		M = null, N = null;
	}
	flush() {
		try {
			Ct = !0, M = this, this.#m();
		} finally {
			Et = 0, xt = null, wt = null, Tt = null, Ct = !1, M = null, N = null, Lt.clear();
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
		return (this.#i ??= b()).promise;
	}
	static ensure() {
		if (M === null) {
			let t = M = new e();
			!Ct && !St && Ze(() => {
				t.started || t.flush();
			});
		}
		return M;
	}
	apply() {
		N = null;
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
			if (Qe(), M === null) return r;
			M.flush();
		}
	} finally {
		St = t, bt = n;
	}
}
function At() {
	try {
		Le();
	} catch (e) {
		ln(e, xt);
	}
}
var jt = null;
function Mt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && qn(r) && (jt = /* @__PURE__ */ new Set(), $n(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && On(r), jt?.size > 0)) {
				Lt.clear();
				for (let e of jt) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) jt.has(n) && (jt.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || $n(n);
					}
				}
				jt.clear();
			}
		}
		jt = null;
	}
}
function Nt(e) {
	M.schedule(e);
}
function Pt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), j(e, x);
		for (var n = e.first; n !== null;) Pt(n, t), n = n.next;
	}
}
function Ft(e) {
	j(e, x);
	for (var t = e.first; t !== null;) Ft(t), t = t.next;
}
// node_modules/svelte/src/internal/client/reactivity/sources.js
var It = /* @__PURE__ */ new Set(), Lt = /* @__PURE__ */ new Map(), Rt = !1;
function zt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Oe,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Bt(e, t) {
	let n = zt(e, t);
	return Bn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function P(t, n = !1, r = !0) {
	let i = zt(t);
	return n || (i.equals = Ae), e && r && A !== null && A.l !== null && (A.l.s ??= []).push(i), i;
}
function F(e, t, n = !1) {
	return H !== null && (!Ln || H.f & 131072) && Je() && H.f & 4325394 && (zn === null || !zn.has(e)) && He(), Ut(e, n ? qt(t) : t, Tt);
}
var Vt = null, Ht = 0;
function Ut(e, t, n = null) {
	if (!e.equals(t)) {
		Fn ? Lt.set(e, t) : Lt.has(e) || Lt.set(e, e.v);
		var r = Ot.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && ht(t), N === null && et(t);
		}
		e.wv = Kn(), Vt = null, Ht = 0, Kt(e, S, n), Vt = null, Je() && W !== null && W.f & 1024 && !(W.f & 96) && (q === null ? Vn([e]) : q.push(e)), !r.is_fork && It.size > 0 && !Rt && Wt();
	}
	return t;
}
function Wt() {
	Rt = !1;
	for (let e of It) {
		e.f & 1024 && j(e, C);
		let t;
		try {
			t = qn(e);
		} catch {
			t = !0;
		}
		t && $n(e);
	}
	It.clear();
}
function Gt(e) {
	F(e, e.v + 1);
}
function Kt(e, t, n) {
	var r = e.reactions;
	if (r !== null) {
		var i = Je(), a = r.length;
		if (Ht += a, Ht > 1e5 && Vt === null && (Vt = /* @__PURE__ */ new Set()), Vt !== null) {
			if (Vt.has(e)) return;
			Vt.add(e);
		}
		for (var o = 0; o < a; o++) {
			var s = r[o], c = s.f;
			if (i || s !== W) {
				var l = (c & S) === 0;
				if (l && j(s, t), c & 131072) It.add(s);
				else if (c & 2) {
					var u = s;
					N?.delete(u), Kt(u, C, n);
				} else if (l) {
					var d = s;
					c & 16 && jt !== null && jt.add(d), n === null ? Nt(d) : n.push(d);
				}
			}
		}
	}
}
function qt(e) {
	if (typeof e != "object" || !e || le in e || ue in e) return e;
	let t = h(e);
	if (t !== p && t !== m) return e;
	var n = /* @__PURE__ */ new Map(), i = a(e), o = /* @__PURE__ */ Bt(0), s = null, c = Wn, l = (e) => {
		if (Wn === c) return e();
		var t = H, n = Wn;
		U(null), Gn(c);
		var r = e();
		return U(t), Gn(n), r;
	};
	return i && n.set("length", /* @__PURE__ */ Bt(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			"value" in r && r.configurable !== !1 && r.enumerable !== !1 && r.writable !== !1 || Be();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Bt(r.value, s);
				return n.set(t, e), e;
			}) : F(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var i = n.get(t);
			if (i === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Bt(r, s));
					n.set(t, e), Gt(o);
				}
			} else F(i, r), Gt(o);
			return !0;
		},
		get(t, i, a) {
			if (i === le) return e;
			var o = n.get(i), c = i in t;
			if (o === void 0 && (!c || d(t, i)?.writable) && (o = l(() => /* @__PURE__ */ Bt(qt(c ? t[i] : r), s)), n.set(i, o)), o !== void 0) {
				var u = J(o);
				return u === r ? void 0 : u;
			}
			return Reflect.get(t, i, a);
		},
		getOwnPropertyDescriptor(e, t) {
			this.has?.(e, t);
			var i = Reflect.getOwnPropertyDescriptor(e, t), a = n.get(t);
			if (a !== void 0) {
				var o = J(a);
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
			if (t === le) return !0;
			var i = n.get(t), a = i !== void 0 && i.v !== r || Reflect.has(e, t);
			return (i !== void 0 || (W !== null || H !== null) && (!a || d(e, t)?.writable)) && (i === void 0 && (i = l(() => /* @__PURE__ */ Bt(a ? qt(e[t]) : r, s)), n.set(t, i)), J(i) === r) ? !1 : a;
		},
		set(e, t, a, c) {
			var u = n.get(t), f = t in e;
			if (i && t === "length") for (var p = a; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Bt(r, s)), n.set(p + "", m)) : F(m, r);
			}
			if (u === void 0) (!f || d(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Bt(void 0, s)), F(u, qt(a)), n.set(t, u));
			else {
				f = u.v !== r;
				var h = l(() => qt(a));
				F(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, a), !f) {
				if (i && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && F(_, v + 1);
				}
				Gt(o);
			}
			return !0;
		},
		ownKeys(e) {
			J(o);
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
var Jt, Yt, Xt, Zt;
function Qt() {
	if (Jt === void 0) {
		Jt = window, Yt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Xt = d(t, "firstChild").get, Zt = d(t, "nextSibling").get, g(e) && (e[me] = void 0, e[pe] = null, e[he] = void 0, e.__e = void 0), g(n) && (n[ge] = void 0);
	}
}
function I(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function $t(e) {
	return Xt.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function en(e) {
	return Zt.call(e);
}
function L(e, t) {
	if (!E) return /* @__PURE__ */ $t(e);
	var n = /* @__PURE__ */ $t(D);
	if (n === null) n = D.appendChild(I());
	else if (t && n.nodeType !== 3) {
		var r = I();
		return n?.before(r), O(r), r;
	}
	return t && sn(n), O(n), n;
}
function tn(e, t = !1) {
	if (!E) {
		var n = /* @__PURE__ */ $t(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ en(n) : n;
	}
	if (t) {
		if (D?.nodeType !== 3) {
			var r = I();
			return D?.before(r), O(r), r;
		}
		sn(D);
	}
	return D;
}
function nn(e, t = !1) {
	if (!E) return /* @__PURE__ */ $t(e);
	var n = L(e, t);
	return k(e), n;
}
function R(e, t = 1, n = !1) {
	let r = E ? D : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ en(r);
	if (!E) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = I();
			return r === null ? i?.after(a) : r.before(a), O(a), a;
		}
		sn(r);
	}
	return O(r), r;
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
	var t = W;
	if (t === null) return H.f |= ce, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	ln(e, t);
}
function ln(e, t) {
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
function un(e) {
	W === null && (H === null && Ie(e), Fe()), Fn && Pe(e);
}
function dn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function z(e, t) {
	var n = W;
	n !== null && n.f & 8192 && (e |= ee);
	var r = {
		ctx: A,
		deps: null,
		nodes: null,
		f: e | S | 512,
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
	M?.register_created_effect(r);
	var i = r;
	if (e & 4) wt === null ? Ot.ensure().schedule(r) : wt.push(r);
	else if (t !== null) {
		try {
			$n(r);
		} catch (e) {
			throw V(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= w));
	}
	if (i !== null && (i.parent = n, n !== null && dn(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function fn() {
	return H !== null && !Ln;
}
function pn(e) {
	let t = z(8, null);
	return j(t, x), t.teardown = e, t;
}
function mn(e) {
	un("$effect");
	var t = W.f;
	if (!H && t & 32 && A !== null && !A.i) {
		var n = A;
		(n.e ??= []).push(e);
	} else return hn(e);
}
function hn(e) {
	return z(4 | ie, e);
}
function gn(e) {
	return un("$effect.pre"), z(8 | ie, e);
}
function _n(e) {
	Ot.ensure();
	let t = z(64 | T, e);
	return () => {
		V(t);
	};
}
function vn(e) {
	Ot.ensure();
	let t = z(64 | T, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? kn(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function yn(e) {
	return z(4, e);
}
function bn(e) {
	return z(se | T, e);
}
function xn(e, t = 0) {
	return z(8 | t, e);
}
function Sn(e, t = [], n = [], r = []) {
	ot(r, t, n, (t) => {
		z(8, () => {
			e(...t.map(J));
		});
	});
}
function Cn(e, t = 0) {
	return z(16 | t, e);
}
function B(e) {
	return z(32 | T, e);
}
function wn(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = Fn, r = H;
		In(!0), U(null);
		try {
			t.call(null);
		} catch (t) {
			ln(t, e.parent);
		} finally {
			In(n), U(r);
		}
	}
}
function Tn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && it(() => {
			e.abort(ve);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function En(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Dn(e.nodes.start, e.nodes.end), n = !0), e.f |= re, Tn(e, t && !n), Qn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	wn(e), e.f ^= re, e.f |= te;
	var i = e.parent;
	i !== null && i.first !== null && On(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Dn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ en(e);
		e.remove(), e = n;
	}
}
function On(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function kn(e, t, n = !0) {
	var r = [];
	e.f |= 256, An(e, r, !0);
	var i = () => {
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function An(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ee;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = !!(i.f & 65536) || !!(i.f & 32) && !!(e.f & 16);
				An(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function jn(e) {
	e.f &= -257, Mn(e, !0);
}
function Mn(e, t) {
	if (!(e.f & 256) && e.f & 8192) {
		e.f ^= ee, e.f & 1024 || (j(e, S), Ot.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = !!(n.f & 65536) || !!(n.f & 32);
			Mn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Nn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ en(n);
		t.append(n), n = i;
	}
}
// node_modules/svelte/src/internal/client/legacy.js
var Pn = null, Fn = !1;
function In(e) {
	Fn = e;
}
var H = null, Ln = !1;
function U(e) {
	H = e;
}
var W = null;
function Rn(e) {
	W = e;
}
var zn = null;
function Bn(e) {
	H !== null && (H.f & 2097152 || H.f & 2) && (zn ??= /* @__PURE__ */ new Set()).add(e);
}
var G = null, K = 0, q = null;
function Vn(e) {
	q = e;
}
var Hn = 1, Un = 0, Wn = Un;
function Gn(e) {
	Wn = e;
}
function Kn() {
	return ++Hn;
}
function qn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (qn(a) && gt(a), a.wv > e.wv) return !0;
		}
		t & 512 && N === null && j(e, x);
	}
	return !1;
}
function Jn(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(zn !== null && zn.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? Jn(a, t, !1) : t === a && (n ? j(a, S) : a.f & 1024 && j(a, C), Nt(a));
	}
}
function Yn(e) {
	var t = G, n = K, r = q, i = H, a = zn, o = A, s = Ln, c = Wn, l = e.f;
	G = null, K = 0, q = null, H = l & 96 ? null : e, zn = null, We(e.ctx), Ln = !1, Wn = ++Un, e.ac !== null && (it(() => {
		e.ac.abort(ve);
	}), e.ac = null);
	try {
		e.f |= oe;
		var u = e.fn, d = u();
		e.f |= ne;
		var f = Xn(e);
		if (Je() && q !== null && !Ln && f !== null && !(e.f & 6146)) for (var p = 0; p < q.length; p++) Jn(q[p], e);
		if (i !== null && i !== e) {
			if (Un++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Un;
			if (t !== null) for (let e of t) e.rv = Un;
			q !== null && (r === null ? r = q : r.push(...q));
		}
		return e.f & 8388608 && (e.f ^= ce), d;
	} catch (t) {
		return Xn(e), cn(t);
	} finally {
		e.f ^= oe, G = t, K = n, q = r, H = i, zn = a, We(o), Ln = s, Wn = c;
	}
}
function Xn(e) {
	var t = e.deps, n = M?.is_fork;
	if (G !== null) {
		var r;
		if (n || Qn(e, K), t !== null && K > 0) for (t.length = K + G.length, r = 0; r < G.length; r++) t[K + r] = G[r];
		else e.deps = t = G;
		if (fn() && e.f & 512) for (r = K; r < t.length; r++) (t[r].reactions ??= []).push(e);
	} else !n && t !== null && K < t.length && (Qn(e, K), t.length = K);
	return t;
}
function Zn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var i = o.call(n, e);
		if (i !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[i] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (G === null || !s.call(G, t))) {
		var c = t;
		c.f & 512 && (c.f ^= 512), c.v !== r && et(c), c.ac !== null && it(() => {
			c.ac.abort(ve), c.ac = null, j(c, S);
		}), _t(c), Qn(c, 0);
	}
}
function Qn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Zn(e, n[r]);
}
function $n(e) {
	var t = e.f;
	if (!(t & 16384)) {
		j(e, x);
		var n = W;
		W = e;
		try {
			t & 16777232 ? En(e) : Tn(e), wn(e);
			var r = Yn(e);
			e.teardown = typeof r == "function" ? r : null, e.wv = Hn;
		} finally {
			W = n;
		}
	}
}
async function er() {
	await Promise.resolve(), kt();
}
function J(e) {
	var t = !!(e.f & 2);
	if (Pn?.add(e), H !== null && !Ln && !(W !== null && W.f & 16384) && (zn === null || !zn.has(e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < Un && (e.rv = Un, G === null && n !== null && n[K] === e ? K++ : G === null ? G = [e] : G.push(e));
		else {
			H.deps ??= [], s.call(H.deps, e) || H.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : s.call(r, H) || r.push(H);
		}
	}
	if (Fn && Lt.has(e)) return Lt.get(e);
	if (t) {
		var i = e;
		if (Fn) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || nr(i)) && (a = ht(i)), Lt.set(i, a), a;
		}
		var o = !(i.f & 512) && !Ln && H !== null && !!(H.f & 512), c = (i.f & ne) === 0;
		qn(i) && (o && (i.f |= 512), gt(i)), o && !c && (vt(i), tr(i));
	}
	if (N?.has(e)) return N.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function tr(e) {
	if (e.f |= 512, e.deps !== null) for (let n of e.deps) {
		var t = n.reactions;
		t === null ? n.reactions = [e] : s.call(t, e) || t.push(e), n.f & 2 && !(n.f & 512) && (vt(n), tr(n));
	}
}
function nr(e) {
	if (e.v === r) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Lt.has(t) || t.f & 2 && nr(t)) return !0;
	return !1;
}
function Y(e) {
	var t = Ln;
	try {
		return Ln = !0, e();
	} finally {
		Ln = t;
	}
}
function rr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (le in e) ir(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && le in n && ir(n);
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
// node_modules/svelte/src/internal/client/dom/elements/events.js
var ar = Symbol("events"), or = /* @__PURE__ */ new Set(), sr = /* @__PURE__ */ new Set();
function cr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || dr.call(t, e), !e.cancelBubble) return it(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? (i.__removed = !1, Ze(() => {
		i.__removed || t.addEventListener(e, i, r);
	})) : t.addEventListener(e, i, r), i;
}
function X(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = cr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && pn(() => {
		o.__removed = !0, t.removeEventListener(e, o, a);
	});
}
var lr = null, ur = !1;
function dr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	lr = e, ur || (ur = !0, setTimeout(() => {
		ur = !1, lr = null;
	}));
	var o = 0, s = lr === e && e[ar];
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
		var d = H, f = W;
		U(null), Rn(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[ar]?.[r];
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
			e[ar] = t, delete e.currentTarget, U(d), Rn(f);
		}
	}
}
// node_modules/svelte/src/internal/client/dom/reconciler.js
var fr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function pr(e) {
	return fr?.createHTML(e) ?? e;
}
function mr(e) {
	var t = on("template");
	return t.innerHTML = pr(e.replaceAll("<!>", "<!---->")), t.content;
}
// node_modules/svelte/src/internal/client/dom/template.js
function hr(e, t) {
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
		if (E) return hr(D, null), D;
		i === void 0 && (i = mr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ $t(i)));
		var t = r || Yt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ $t(t), s = t.lastChild;
			hr(o, s);
		} else hr(t, t);
		return t;
	};
}
function Q(e, t) {
	if (E) {
		var n = W;
		n.f & 32768 && n.nodes.end !== null || (n.nodes.end = D), we();
	} else e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var gr = ["touchstart", "touchmove"];
function _r(e) {
	return gr.includes(e);
}
// node_modules/svelte/src/reactivity/create-subscriber.js
function vr(e) {
	let t = 0, n = zt(0), r;
	return () => {
		fn() && (J(n), xn(() => (t === 0 && (r = Y(() => e(() => Gt(n)))), t += 1, () => {
			Ze(() => {
				--t, t === 0 && (r?.(), r = void 0, Gt(n));
			});
		})));
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var yr = w | T;
function br(e, t, n, r) {
	new xr(e, t, n, r);
}
var xr = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = E ? D : null;
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
	#m = vr(() => (this.#p = zt(this.#l), () => {
		this.#p = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = W;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = W.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Cn(() => {
			if (E) {
				let e = De(this.#t);
				we();
				let t = e === "[!";
				if (e.startsWith("[?")) {
					let t = JSON.parse(e.slice(2));
					this.#g(t);
				} else t ? this.#y() : this.#h();
			} else this.#b();
		}, yr), E && (this.#e = D);
	}
	#h() {
		try {
			this.#a = B(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#g(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#_(e);
		Ze(r), t && (this.#s = B(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#_(e) {
		var t = !1, n = !1;
		let r = () => {
			this.#v() || (t ? Se() : (t = !0, n && Ue(), this.#s !== null && kn(this.#s, () => {
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
					ln(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#v() {
		return (this.#i.f & (te | re)) !== 0;
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = B(() => e(this.#e)), Ze(() => {
			if (!this.#v()) {
				var e = this.#c = document.createDocumentFragment(), t = I(), n = !1;
				e.append(t), this.#a = this.#S(() => {
					try {
						return B(() => this.#r(t));
					} catch (e) {
						try {
							this.error(e), n = !0;
						} catch (e) {
							ln(e, this.#i.parent);
						}
						return null;
					}
				}), this.#a === null ? (this.#c = null, n && this.#x(M)) : this.#u === 0 && (this.#e.before(e), this.#c = null, kn(this.#o, () => {
					this.#o = null;
				}), this.#x(M));
			}
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = B(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Nn(this.#a, e);
				let t = this.#n.pending;
				this.#o = B(() => t(this.#e));
			} else this.#x(M);
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
		var t = W, n = H, r = A;
		Rn(this.#i), U(this.#i), We(this.#i.ctx);
		try {
			return Ot.ensure(), e();
		} finally {
			Rn(t), U(n), We(r);
		}
	}
	#C(e, t) {
		this.has_pending_snippet() ? (this.#u += e, this.#u === 0 && (this.#x(t), this.#o && kn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null))) : this.parent && this.parent.#C(e, t);
	}
	update_pending_count(e, t) {
		this.#C(e, t), this.#l += e, !this.#p || this.#d || (this.#d = !0, Ze(() => {
			this.#d = !1, this.#p && Ut(this.#p, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#m(), J(this.#p);
	}
	error(e) {
		if (e === n || !this.#n.onerror && !this.#n.failed) throw e;
		M?.is_fork ? (this.#a && M.skip_effect(this.#a), this.#o && M.skip_effect(this.#o), this.#s && M.skip_effect(this.#s), M.oncommit(() => {
			this.#v() || this.#w(e);
		})) : this.#w(e);
	}
	#w(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), E && (O(this.#t), Te(), O(Ee()));
		let t = this.#n.failed, n = (e) => {
			if (this.#v()) return;
			let { reset: n, invoke_onerror: r } = this.#_(e);
			r(), t && !this.#v() && (this.#s = this.#S(() => {
				try {
					return B(() => {
						var r = W;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return ln(e, this.#i.parent), null;
				}
			}));
		};
		Ze(() => {
			if (!this.#v()) {
				var t;
				try {
					t = this.transform_error(e);
				} catch (e) {
					ln(e, this.#i && this.#i.parent);
					return;
				}
				typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => ln(e, this.#i && this.#i.parent)) : n(t);
			}
		});
	}
};
function Sr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[ge] ??= e.nodeValue) && (e[ge] = n, e.nodeValue = `${n}`);
}
function Cr(e, t) {
	return Er(e, t);
}
function wr(e, t) {
	Qt(), t.intro = t.intro ?? !1;
	let r = t.target, i = E, a = D;
	try {
		for (var o = /* @__PURE__ */ $t(r); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ en(o);
		if (!o) throw n;
		Ce(!0), O(o);
		let i = Er(e, {
			...t,
			anchor: o
		});
		return Ce(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== n && console.warn("Failed to hydrate: ", i), t.recover === !1 && Re(), Qt(), rn(r), Ce(!1), Cr(e, t);
	} finally {
		Ce(i), O(a);
	}
}
var Tr = /* @__PURE__ */ new Map();
function Er(e, { target: t, anchor: r, props: i = {}, events: a, context: o, intro: s = !0, transformError: l }) {
	Qt();
	var u = void 0, d = vn(() => {
		var s = r ?? t.appendChild(I());
		br(s, { pending: () => {} }, (t) => {
			Ge({});
			var r = A;
			if (o && (r.c = o), a && (i.$$events = a), E && hr(t, null), u = e(t, i) || qe(), E && (W.nodes.end = D, D === null || D.nodeType !== 8 || D.data !== "]")) throw xe(), n;
			Ke();
		}, l);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = _r(r);
					for (let e of [t, document]) {
						var a = Tr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), Tr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, dr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(c(or)), sr.add(f), () => {
			for (var e of d) for (let r of [t, document]) {
				var n = Tr.get(r), i = n.get(e);
				--i == 0 ? (r.removeEventListener(e, dr), n.delete(e), n.size === 0 && Tr.delete(r)) : n.set(e, i);
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
// node_modules/svelte/src/internal/client/dom/blocks/branches.js
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
			if (n) jn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (jn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
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
						Nn(r, t), t.append(I()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), kn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = M, r = an();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = document.createDocumentFragment(), a = I();
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
		} else E && (this.anchor = D), this.#a(n);
	}
};
function Ar(t) {
	A === null && je("onMount"), e && A.l !== null ? jr(A).m.push(t) : mn(() => {
		let e = Y(t);
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
// node_modules/svelte/src/internal/client/dom/blocks/if.js
function $(e, t, n = !1) {
	var r;
	E && (r = D, we());
	var i = new kr(e), a = n ? w : 0;
	function o(e, t) {
		if (E) {
			var n = De(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Ee();
				O(a), i.anchor = a, Ce(!1), i.ensure(e, t), Ce(!0);
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
// node_modules/svelte/src/internal/client/dom/blocks/each.js
function Mr(e, t) {
	return t;
}
function Nr(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		kn(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					Pr(e, c(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var l = r.length === 0 && n !== null && e.pending.size === 0;
		if (l) {
			var u = n, d = u.parentNode;
			rn(d), d.append(u), e.items.clear();
		}
		Pr(e, t, !l);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function Pr(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= ae, Nn(a, document.createDocumentFragment())) : V(t[i], n);
	}
}
var Fr;
function Ir(e, t, n, r, i, o = null) {
	var s = e, l = /* @__PURE__ */ new Map();
	if (t & 4) {
		var u = e;
		s = E ? O(/* @__PURE__ */ $t(u)) : u.appendChild(I());
	}
	E && we();
	var d = null, f = /* @__PURE__ */ pt(() => {
		var e = n();
		return a(e) ? e : e == null ? [] : c(e);
	}), p = /* @__PURE__ */ new Map(), m = !0;
	function h(e) {
		if (!(_.effect.f & 16384)) {
			_.pending.delete(e);
			var n = J(f);
			_.fallback = d, Rr(_, n, s, t, r), d !== null && (n.length === 0 ? d.f & 33554432 ? (d.f ^= ae, Br(d, null, s)) : jn(d) : kn(d, () => {
				d = null;
			}));
		}
	}
	function g(e) {
		_.pending.delete(e);
	}
	var _ = {
		effect: Cn(() => {
			var e = J(f), a = e.length;
			let c = !1;
			E && De(s) === "[!" != (a === 0) && (s = Ee(), O(s), Ce(!1), c = !0);
			for (var u = /* @__PURE__ */ new Set(), _ = M, v = an(), y = 0; y < a; y += 1) {
				E && D.nodeType === 8 && D.data === "]" && (s = D, c = !0, Ce(!1));
				var b = e[y], x = r(b, y), S = m ? null : l.get(x);
				S ? (S.v && Ut(S.v, b), S.i && Ut(S.i, y), v && _.unskip_effect(S.e)) : (S = zr(l, m ? s : Fr ??= I(), b, x, y, i, t, n), m || (S.e.f |= ae), l.set(x, S)), u.add(x);
			}
			if (a === 0 && o && !d && (m ? d = B(() => o(s)) : (d = B(() => o(Fr ??= I())), d.f |= ae)), a > u.size && Ne("", "", ""), E && a > 0 && O(Ee()), !m) {
				if (p.set(_, u), v) {
					for (let [e, t] of l) u.has(e) || _.skip_effect(t.e);
					_.oncommit(h), _.ondiscard(g);
				} else h(_);
			}
			c && Ce(!0), J(f);
		}),
		flags: t,
		items: l,
		pending: p,
		outrogroups: null,
		fallback: d
	};
	m = !1, E && (s = D);
}
function Lr(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function Rr(e, t, n, r, i) {
	var a = !!(r & 8), o = t.length, s = e.items, l = Lr(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (jn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) {
			if (_.f ^= ae, _ === l) Br(_, null, n);
			else {
				var y = d ? d.next : l;
				_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), Vr(e, d, _), Vr(e, _, y), Br(_, y, n), d = _, p = [], m = [], l = Lr(d.next);
				continue;
			}
		}
		if (_ !== l) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) Br(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					Vr(e, S.prev, C.next), Vr(e, d, S), Vr(e, C, b), l = b, d = C, --v, p = [], m = [];
				} else u.delete(_), Br(_, l, n), Vr(e, _.prev, _.next), Vr(e, _, d === null ? e.effect.first : d.next), Vr(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; l !== null && l !== _;) (u ??= /* @__PURE__ */ new Set()).add(l), m.push(l), l = Lr(l.next);
			if (l === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, l = Lr(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (Pr(e, c(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (l !== null || u !== void 0) {
		var ee = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || ee.push(_);
		for (; l !== null;) !(l.f & 8192) && l !== e.fallback && ee.push(l), l = Lr(l.next);
		var te = ee.length;
		if (te > 0) {
			var ne = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < te; v += 1) ee[v].nodes?.a?.measure();
				for (v = 0; v < te; v += 1) ee[v].nodes?.a?.fix();
			}
			Nr(e, ee, ne);
		}
	}
	a && Ze(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function zr(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? zt(n) : /* @__PURE__ */ P(n, !1, !1) : null, l = o & 2 ? zt(i) : null;
	return {
		v: c,
		i: l,
		e: B(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function Br(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ en(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function Vr(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
// node_modules/svelte/src/internal/client/dom/css.js
function Hr(e, t) {
	yn(() => {
		e = W?.parent?.nodes?.start ?? e;
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = on("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
// node_modules/svelte/src/internal/shared/attributes.js
var Ur = [..." 	\n\r\f\xA0\v﻿"];
function Wr(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Ur.includes(r[o - 1])) && (s === r.length || Ur.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
// node_modules/svelte/src/internal/client/dom/elements/class.js
function Gr(e, t, n, r, i, a) {
	var o = e[me];
	if (E || o !== n || o === void 0) {
		var s = Wr(n, r, a);
		E && s === e.getAttribute("class") || (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e[me] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
// node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Kr = Symbol("is custom element"), qr = Symbol("is html"), Jr = ye ? "link" : "LINK", Yr = ye ? "progress" : "PROGRESS";
function Xr(e) {
	if (E) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Qr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Qr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[_e] = n, Ze(n), rt();
	}
}
function Zr(e, t) {
	var n = $r(e);
	n.value !== (n.value = t ?? void 0) && (e.value !== t || t === 0 && e.nodeName === Yr) && (e.value = t ?? "");
}
function Qr(e, t, n, r) {
	var i = $r(e);
	if (!(E && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Jr))) {
		var a = i[t];
		a !== (i[t] = n) && (t === "loading" && (e[fe] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && ti(e).has(t) ? e[t] = n : (!E || typeof n != "number" && typeof n != "boolean" || a !== String(n)) && e.setAttribute(t, n));
	}
}
function $r(e) {
	return e[pe] ??= {
		[Kr]: e.nodeName.includes("-"),
		[qr]: e.namespaceURI === i
	};
}
var ei = /* @__PURE__ */ new Map();
function ti(e) {
	var t = e.getAttribute("is") || e.nodeName, n = ei.get(t);
	if (n) return n;
	ei.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = f(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.add(o);
		i = h(i);
	}
	return n;
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function ni(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	at(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = ri(e) ? ii(a) : a, n(a), M !== null && r.add(M), await er(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (E && e.defaultValue !== e.value || Y(t) == null && e.value) && (n(ri(e) ? ii(e.value) : e.value), M !== null && r.add(M)), xn(() => {
		var n = t();
		if (e === document.activeElement) {
			var i = M;
			if (r.has(i)) return;
		}
		ri(e) && n === ii(e.value) || (e.type !== "date" || n || e.value) && n !== e.value && (e.value = n ?? "");
	});
}
function ri(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function ii(e) {
	return e === "" ? null : +e;
}
// node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function ai(e) {
	return function(...t) {
		return t[0].stopPropagation(), e?.apply(this, t);
	};
}
// node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function oi(e = !1) {
	let t = A, n = t.l.u;
	if (!n) return;
	let r = () => rr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ ut(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => J(i);
	}
	n.b.length && gn(() => {
		si(t, r), y(n.b);
	}), mn(() => {
		let e = Y(() => n.m.map(v));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && mn(() => {
		si(t, r), y(n.a);
	});
}
function si(e, t) {
	if (e.l.s) for (let t of e.l.s) J(t);
	t();
}
// node_modules/svelte/src/internal/client/dom/legacy/misc.js
function ci(e, t) {
	var n = e.$$events?.[t.type];
	for (var r of a(n) ? n.slice() : n == null ? [] : [n]) r.call(this, t);
}
// node_modules/svelte/src/internal/client/reactivity/store.js
var li = !1;
function ui(e) {
	var t = li;
	try {
		return li = !1, [e(), li];
	} finally {
		li = t;
	}
}
// node_modules/svelte/src/internal/client/reactivity/props.js
function di(t, n, r, i) {
	var a = !e || !!(r & 2), o = !!(r & 8), s = !!(r & 16), c = i, l = !0, u = void 0, f = () => s && a ? (u ??= /* @__PURE__ */ ut(i), J(u)) : (l && (l = !1, c = s ? Y(i) : i), c);
	let p;
	if (o) {
		var m = le in t || de in t;
		p = d(t, n)?.set ?? (m && n in t ? (e) => t[n] = e : void 0);
	}
	var h, g = !1;
	o ? [h, g] = ui(() => t[n]) : h = t[n], h === void 0 && i !== void 0 && (h = f(), p && (a && ze(n), p(h)));
	var _ = a ? () => {
		var e = t[n];
		return e === void 0 ? f() : (l = !0, e);
	} : () => {
		var e = t[n];
		return e !== void 0 && (c = void 0), e === void 0 ? c : e;
	};
	if (a && !(r & 4)) return _;
	if (p) {
		var v = t.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || v || g) && p(t ? _() : e), e) : _();
		});
	}
	var y = !1, b = (r & 1 ? ut : pt)(() => (y = !1, _()));
	o && J(b);
	var x = W;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? J(b) : a && o ? qt(e) : e;
			return F(b, n), y = !0, c !== void 0 && (c = n), e;
		}
		return Fn && y || x.f & 16384 ? b.v : J(b);
	});
}
// node_modules/svelte/src/legacy/legacy-client.js
function fi(e) {
	return new pi(e);
}
var pi = class {
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
				return J(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === de || (J(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return F(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
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
}, mi;
typeof HTMLElement == "function" && (mi = class extends HTMLElement {
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
					e !== "default" && (n.name = e), Q(t, n);
				};
			}
			let t = {}, n = gi(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = hi(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = fi({
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
						let t = hi(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = hi(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
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
function hi(e, t, n, r) {
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
function gi(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function _i(e, t, n, r, i, a) {
	let o = class extends mi {
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
				n = hi(e, n, t), this.$$d[e] = n;
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
// MusicBrainzCard.svelte
var vi = /* @__PURE__ */ Z("<div class=\"loading-state svelte-1ghyjz5\">Loading...</div>"), yi = /* @__PURE__ */ Z("<div class=\"redirect-copy-group svelte-1ghyjz5\"><input type=\"text\" class=\"input-field readonly svelte-1ghyjz5\" readonly=\"\"/> <button class=\"btn-primary svelte-1ghyjz5\">Copy</button></div>"), bi = /* @__PURE__ */ Z("<button class=\"btn-ghost svelte-1ghyjz5\">+ Add Account</button>"), xi = /* @__PURE__ */ Z("<span class=\"status-badge success svelte-1ghyjz5\">✓ Authenticated</span>"), Si = /* @__PURE__ */ Z("<span class=\"status-badge warning svelte-1ghyjz5\">⚠ Not Authenticated</span>"), Ci = /* @__PURE__ */ Z("<span class=\"status-badge active svelte-1ghyjz5\">● Active</span>"), wi = /* @__PURE__ */ Z("<div class=\"account-item svelte-1ghyjz5\"><div class=\"account-info svelte-1ghyjz5\"><div class=\"account-name svelte-1ghyjz5\"> </div> <div class=\"account-badges svelte-1ghyjz5\"><!> <!></div></div> <div class=\"account-actions svelte-1ghyjz5\"><button class=\"link-btn svelte-1ghyjz5\"> </button> <button> </button> <button class=\"btn-danger svelte-1ghyjz5\">✕</button></div></div>"), Ti = /* @__PURE__ */ Z("<div class=\"empty-accounts svelte-1ghyjz5\">No accounts linked.</div>"), Ei = /* @__PURE__ */ Z("<div class=\"settings-section svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">Server Configuration</h3> <div class=\"form-grid svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">API Base URL</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"https://musicbrainz.org/ws/2\"/> <p class=\"helper-text svelte-1ghyjz5\">Point this to a local MusicBrainz container for offline use.</p></label> <button class=\"btn-primary svelte-1ghyjz5\">Save Settings</button></div></div> <div class=\"settings-section svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">OAuth Credentials</h3> <div class=\"form-grid svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Client ID</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"Enter Client ID\"/></label> <label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Client Secret</span> <div class=\"password-wrapper svelte-1ghyjz5\"><input class=\"input-field svelte-1ghyjz5\"/> <button class=\"toggle-visibility svelte-1ghyjz5\"> </button></div></label> <button class=\"btn-primary svelte-1ghyjz5\"> </button></div></div> <div class=\"settings-section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">Redirect URI</h3> <button class=\"btn-ghost svelte-1ghyjz5\"> </button></div> <!></div> <div class=\"settings-section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\"> </h3> <!></div> <div class=\"accounts-list svelte-1ghyjz5\"></div></div>", 1), Di = /* @__PURE__ */ Z("<div class=\"modal-overlay svelte-1ghyjz5\"><div class=\"modal-content svelte-1ghyjz5\"><div class=\"modal-header svelte-1ghyjz5\"><h3 class=\"modal-title svelte-1ghyjz5\">Add MusicBrainz Account</h3> <button class=\"close-btn svelte-1ghyjz5\">✕</button></div> <div class=\"modal-body svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Display Name</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"My Account\"/></label></div> <div class=\"modal-footer svelte-1ghyjz5\"><button class=\"btn-ghost svelte-1ghyjz5\">Cancel</button> <button class=\"btn-primary svelte-1ghyjz5\">Add</button></div></div></div>"), Oi = /* @__PURE__ */ Z("<section class=\"plugin-card svelte-1ghyjz5\"><div class=\"card-header svelte-1ghyjz5\"><div class=\"header-left svelte-1ghyjz5\"><h2 class=\"card-title svelte-1ghyjz5\">MusicBrainz</h2> <span class=\"type-badge svelte-1ghyjz5\">Metadata Provider</span></div></div> <!></section> <!>", 1), ki = {
	hash: "svelte-1ghyjz5",
	code: ".plugin-card.svelte-1ghyjz5 {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border-subtle, #1e293b);}.header-left.svelte-1ghyjz5 {display:flex;align-items:center;gap:12px;}.card-title.svelte-1ghyjz5 {margin:0;font-size:20px;font-weight:700;}.type-badge.svelte-1ghyjz5 {font-size:11px;padding:4px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-1ghyjz5 {padding:24px;text-align:center;color:var(--text-secondary, #cbd5e1);}.settings-section.svelte-1ghyjz5 {margin-bottom:24px;}.section-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;}.section-title.svelte-1ghyjz5 {margin:0;font-size:16px;font-weight:600;}.form-grid.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:16px;}.form-field.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:8px;}.field-label.svelte-1ghyjz5 {font-size:13px;font-weight:500;color:var(--text-secondary, #cbd5e1);}.input-field.svelte-1ghyjz5 {width:100%;padding:10px 14px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);border-radius:8px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.2s;}.input-field.svelte-1ghyjz5:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.input-field.readonly.svelte-1ghyjz5 {opacity:0.6;cursor:not-allowed;}.btn-primary.svelte-1ghyjz5 {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-1ghyjz5:hover:not(:disabled) {opacity:0.9;}.btn-primary.svelte-1ghyjz5:disabled {opacity:0.5;cursor:not-allowed;}.btn-ghost.svelte-1ghyjz5 {padding:8px 16px;background:rgba(255, 255, 255, 0.05);border:1px solid rgba(255, 255, 255, 0.1);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.svelte-1ghyjz5:hover {background:rgba(255, 255, 255, 0.1);}.btn-ghost.active.svelte-1ghyjz5 {border-color:var(--color-primary, #14b8a6);color:var(--color-primary, #14b8a6);}.btn-danger.svelte-1ghyjz5 {background:rgba(239, 68, 68, 0.15);color:#ef4444;border:none;padding:8px 12px;border-radius:6px;cursor:pointer;}.helper-text.svelte-1ghyjz5 {font-size:11px;color:var(--text-secondary, #cbd5e1);margin-top:4px;}.redirect-copy-group.svelte-1ghyjz5 {display:flex;gap:8px;align-items:stretch;}.redirect-copy-group.svelte-1ghyjz5 .input-field:where(.svelte-1ghyjz5) {flex:1;font-family:monospace;}.accounts-list.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:8px;}.account-item.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:rgba(255, 255, 255, 0.03);border:1px solid rgba(255, 255, 255, 0.05);border-radius:8px;}.account-info.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:4px;}.account-name.svelte-1ghyjz5 {font-weight:600;font-size:14px;}.account-badges.svelte-1ghyjz5 {display:flex;gap:8px;}.status-badge.svelte-1ghyjz5 {font-size:10px;padding:2px 6px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-1ghyjz5 {background:rgba(34, 197, 94, 0.15);color:#22c55e;}.status-badge.warning.svelte-1ghyjz5 {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-1ghyjz5 {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.account-actions.svelte-1ghyjz5 {display:flex;gap:12px;align-items:center;}.link-btn.svelte-1ghyjz5 {background:none;border:none;color:var(--color-primary, #14b8a6);font-size:13px;font-weight:600;cursor:pointer;}.link-btn.svelte-1ghyjz5:hover {text-decoration:underline;}.password-wrapper.svelte-1ghyjz5 {position:relative;display:flex;align-items:center;width:100%;}.toggle-visibility.svelte-1ghyjz5 {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary, #f8fafc);}.modal-overlay.svelte-1ghyjz5 {position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:1000;backdrop-filter:blur(4px);}.modal-content.svelte-1ghyjz5 {background:#0f1216;border:1px solid var(--border-subtle, #1e293b);border-radius:12px;width:100%;max-width:440px;box-shadow:0 24px 48px rgba(0,0,0,0.5);}.modal-header.svelte-1ghyjz5 {padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;justify-content:space-between;align-items:center;}.modal-title.svelte-1ghyjz5 {margin:0;font-size:16px;font-weight:700;}.close-btn.svelte-1ghyjz5 {background:none;border:none;color:var(--text-secondary, #cbd5e1);font-size:20px;cursor:pointer;}.modal-body.svelte-1ghyjz5 {padding:20px;display:flex;flex-direction:column;gap:16px;}.modal-footer.svelte-1ghyjz5 {padding:16px 20px;border-top:1px solid rgba(255,255,255,0.05);display:flex;justify-content:flex-end;gap:12px;}.empty-accounts.svelte-1ghyjz5 {text-align:center;padding:16px;color:var(--text-secondary, #cbd5e1);font-size:13px;background:rgba(255, 255, 255, 0.02);border-radius:8px;border:1px dashed rgba(255, 255, 255, 0.1);}"
};
function Ai(e, t) {
	Ge(t, !1), Hr(e, ki);
	let n = di(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(!0), i = /* @__PURE__ */ P([]), a = /* @__PURE__ */ P(""), o = /* @__PURE__ */ P(""), s = /* @__PURE__ */ P(""), c = /* @__PURE__ */ P(""), l = !1, u = !1, d = /* @__PURE__ */ P(!1), f = /* @__PURE__ */ P(!1), p = /* @__PURE__ */ P(!1), m = /* @__PURE__ */ P("https://musicbrainz.org/ws/2"), h = /* @__PURE__ */ P(!1), g = /* @__PURE__ */ P(""), _ = /* @__PURE__ */ P(!1);
	Ar(async () => {
		await v(), F(r, !1);
	});
	async function v() {
		try {
			let e = await (await fetch(`${n()}/accounts`)).json();
			e && (F(i, e.accounts || []), F(a, e.redirect_uri || ""), l = e.client_id_configured || !1, u = e.client_secret_configured || !1, F(p, !!J(a)));
			let t = await (await fetch(`${n()}/settings`)).json();
			t?.settings && F(m, t.settings.api_base_url || "https://musicbrainz.org/ws/2");
			let r = await (await fetch(`${n()}/credentials`)).json();
			r?.credentials && (F(o, r.credentials.client_id || ""), F(c, u ? "••••••••" : ""));
		} catch (e) {
			console.error("Failed to load MusicBrainz data:", e);
		}
	}
	async function y() {
		if (!J(o).trim()) {
			console.error("Client ID is required");
			return;
		}
		let e = { client_id: J(o) };
		if (J(s).trim()) e.client_secret = J(s);
		else if (!u) {
			console.error("Client Secret is required");
			return;
		}
		try {
			F(f, !0), await fetch(`${n()}/credentials`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ credentials: e })
			}), F(s, ""), await v();
		} catch (e) {
			console.error("Failed to save credentials:", e);
		} finally {
			F(f, !1);
		}
	}
	async function b() {
		try {
			await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ settings: { api_base_url: J(m) } })
			}), console.log("MusicBrainz settings saved");
		} catch (e) {
			console.error("Failed to save settings:", e);
		}
	}
	function x() {
		F(g, ""), F(h, !0);
	}
	function S() {
		F(h, !1), F(g, "");
	}
	async function C() {
		let e = J(g).trim();
		if (e) try {
			F(_, !0), await fetch(`${n()}/accounts`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ account_name: e })
			}), S(), await v();
		} catch (e) {
			console.error("Failed to add account:", e);
		} finally {
			F(_, !1);
		}
	}
	async function ee(e, t) {
		if (confirm(`Delete account "${t}"?`)) try {
			await fetch(`${n()}/accounts/${e}`, { method: "DELETE" }), await v();
		} catch (e) {
			console.error("Failed to delete account:", e);
		}
	}
	async function te(e, t) {
		try {
			await fetch(`${n()}/accounts/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			}), await v();
		} catch (e) {
			console.error("Failed to update account status:", e);
		}
	}
	async function ne(e) {
		if (!l || !u) alert("Save your Client ID and Secret first.");
		else try {
			let t = (await (await fetch(`${n()}/auth?account_id=${e}`)).json())?.auth_url;
			t && (window.open(t, "_blank", "noopener,noreferrer"), setTimeout(() => v(), 5e3));
		} catch (e) {
			console.error("Failed to start OAuth:", e);
		}
	}
	var re = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), kt();
		}
	};
	oi();
	var w = Oi(), T = tn(w), ie = R(L(T), 2), ae = (e) => {
		Q(e, vi());
	}, oe = (e) => {
		var t = Ei(), n = tn(t), r = R(L(n), 2), l = L(r), u = R(L(l), 2);
		Xr(u), Te(2), k(l);
		var h = R(l, 2);
		k(r), k(n);
		var g = R(n, 2), _ = R(L(g), 2), v = L(_), S = R(L(v), 2);
		Xr(S), k(v);
		var C = R(v, 2), re = R(L(C), 2), w = L(re);
		Xr(w);
		var T = R(w, 2), ie = nn(T, !0);
		k(re), k(C);
		var ae = R(C, 2), oe = nn(ae, !0);
		k(_), k(g);
		var se = R(g, 2), ce = L(se), le = R(L(ce), 2), ue = nn(le, !0);
		k(ce);
		var de = R(ce, 2), fe = (e) => {
			var t = yi(), n = L(t);
			Xr(n);
			var r = R(n, 2);
			k(t), Sn(() => Zr(n, J(a))), X("click", r, () => {
				navigator.clipboard.writeText(J(a)), alert("Copied!");
			}), Q(e, t);
		};
		$(de, (e) => {
			J(p) || e(fe);
		}), k(se);
		var pe = R(se, 2), me = L(pe), he = L(me), ge = nn(he), _e = R(he, 2), ve = (e) => {
			var t = bi();
			X("click", t, x), Q(e, t);
		};
		$(_e, (e) => {
			J(i), Y(() => J(i).length < 10) && e(ve);
		}), k(me);
		var ye = R(me, 2);
		Ir(ye, 5, () => J(i), Mr, (e, t) => {
			var n = wi(), r = L(n), i = L(r), a = nn(i, !0), o = R(i, 2), s = L(o), c = (e) => {
				Q(e, xi());
			}, l = (e) => {
				Q(e, Si());
			};
			$(s, (e) => {
				J(t), Y(() => J(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = R(s, 2), d = (e) => {
				Q(e, Ci());
			};
			$(u, (e) => {
				J(t), Y(() => J(t).is_active) && e(d);
			}), k(o), k(r);
			var f = R(r, 2), p = L(f), m = nn(p, !0), h = R(p, 2);
			let g;
			var _ = nn(h, !0), v = R(h, 2);
			k(f), k(n), Sn(() => {
				Sr(a, (J(t), Y(() => J(t).display_name || J(t).account_name))), Sr(m, (J(t), Y(() => J(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), g = Gr(h, 1, "btn-ghost svelte-1ghyjz5", null, g, { active: J(t).is_active }), Sr(_, (J(t), Y(() => J(t).is_active ? "Deactivate" : "Activate")));
			}), X("click", p, () => ne(J(t).id)), X("click", h, () => te(J(t).id, J(t).is_active)), X("click", v, () => ee(J(t).id, J(t).display_name || J(t).account_name)), Q(e, n);
		}, (e) => {
			Q(e, Ti());
		}), k(ye), k(pe), Sn(() => {
			Qr(w, "type", J(d) ? "text" : "password"), Qr(w, "placeholder", J(c) || "Enter Client Secret"), Sr(ie, J(d) ? "🙈" : "👁️"), ae.disabled = J(f), Sr(oe, J(f) ? "Saving..." : "Save Credentials"), Sr(ue, J(p) ? "Expand" : "Collapse"), Sr(ge, `Accounts (${J(i), Y(() => J(i).length) ?? ""}/10)`);
		}), ni(u, () => J(m), (e) => F(m, e)), X("click", h, b), ni(S, () => J(o), (e) => F(o, e)), ni(w, () => J(s), (e) => F(s, e)), X("click", T, () => F(d, !J(d))), X("click", ae, y), X("click", le, () => F(p, !J(p))), Q(e, t);
	};
	$(ie, (e) => {
		J(r) ? e(ae) : e(oe, -1);
	}), k(T);
	var se = R(T, 2), ce = (e) => {
		var n = Di(), r = L(n), i = L(r), a = R(L(i), 2);
		k(i);
		var o = R(i, 2), s = L(o), c = R(L(s), 2);
		Xr(c), k(s), k(o);
		var l = R(o, 2), u = L(l), d = R(u, 2);
		k(l), k(r), k(n), Sn(() => d.disabled = J(_)), X("click", a, S), ni(c, () => J(g), (e) => F(g, e)), X("click", u, S), X("click", d, C), X("click", r, ai(function(e) {
			ci.call(this, t, e);
		})), X("click", n, S), Q(e, n);
	};
	return $(se, (e) => {
		J(h) && e(ce);
	}), Q(e, w), Ke(re);
}
customElements.define("musicbrainz-dashboard-card", _i(Ai, { apiBase: {} }, [], [], { mode: "open" }));
// MusicBrainzSettingsCard.svelte
var ji = /* @__PURE__ */ Z("<div class=\"loading-state svelte-18cwlk6\">Loading configuration…</div>"), Mi = /* @__PURE__ */ Z("<span class=\"status-tag success svelte-18cwlk6\">● Configured</span>"), Ni = /* @__PURE__ */ Z("<div class=\"warning-box svelte-18cwlk6\">⚠ A User Token is required to enable contributions. Please enter your token above.</div>"), Pi = /* @__PURE__ */ Z("<div class=\"feedback error svelte-18cwlk6\"> </div>"), Fi = /* @__PURE__ */ Z("<div class=\"feedback success svelte-18cwlk6\">✓ Configuration saved successfully.</div>"), Ii = /* @__PURE__ */ Z("<div class=\"info-banner svelte-18cwlk6\"><p>MusicBrainz works out-of-the-box for metadata retrieval. An account is only needed for contributing data back to the community.</p></div> <div class=\"form-section svelte-18cwlk6\"><label class=\"field-label svelte-18cwlk6\" for=\"mb-user-token\">User Token / API Key <!></label> <p class=\"helper-text svelte-18cwlk6\">Obtain your personal access token from <a href=\"https://musicbrainz.org/account/applications\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"link svelte-18cwlk6\">musicbrainz.org/account/applications</a>.\n        Required for submitting ISRC codes and metadata corrections.</p> <div class=\"input-wrapper svelte-18cwlk6\"><input id=\"mb-user-token\" class=\"input-field svelte-18cwlk6\"/> <button type=\"button\" class=\"toggle-btn svelte-18cwlk6\"> </button></div></div> <div class=\"toggle-card svelte-18cwlk6\"><div class=\"toggle-header svelte-18cwlk6\"><p class=\"toggle-label svelte-18cwlk6\">Auto-Contribute Missing Data</p> <button type=\"button\" role=\"switch\" aria-label=\"Toggle auto-contribute\"><span class=\"switch-thumb svelte-18cwlk6\"></span></button></div> <p class=\"helper-text mt-2 svelte-18cwlk6\">When enabled, EchoSync will automatically submit missing acoustic fingerprints (AcoustID) and \n        ISRC data back to MusicBrainz during imports.</p> <!></div> <!> <!> <div class=\"actions svelte-18cwlk6\"><button class=\"btn-primary svelte-18cwlk6\"> </button></div>", 1), Li = /* @__PURE__ */ Z("<section class=\"plugin-card svelte-18cwlk6\"><div class=\"card-header svelte-18cwlk6\"><svg width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"accent-icon svelte-18cwlk6\"><circle cx=\"12\" cy=\"12\" r=\"10\"></circle><path d=\"M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3\"></path><line x1=\"12\" y1=\"17\" x2=\"12.01\" y2=\"17\"></line></svg> <div><h2 class=\"card-title svelte-18cwlk6\">MusicBrainz Configuration</h2> <p class=\"card-subtitle svelte-18cwlk6\">Global music encyclopedia & metadata source</p></div> <span class=\"type-badge svelte-18cwlk6\">Metadata</span></div> <!></section>"), Ri = {
	hash: "svelte-18cwlk6",
	code: ".plugin-card.svelte-18cwlk6 {background:var(--bg-surface);backdrop-filter:blur(12px);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);padding:24px;margin-bottom:16px;color:var(--text-primary);}.card-header.svelte-18cwlk6 {display:flex;align-items:center;gap:12px;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle);}.accent-icon.svelte-18cwlk6 {color:var(--color-primary);}.card-title.svelte-18cwlk6 {margin:0;font-size:1.25rem;font-weight:600;line-height:1.2;}.card-subtitle.svelte-18cwlk6 {margin:4px 0 0;font-size:0.75rem;color:var(--text-muted);}.type-badge.svelte-18cwlk6 {margin-left:auto;font-size:11px;padding:4px 8px;background:rgba(16, 185, 129, 0.1);color:#10b981;border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-18cwlk6 {padding:20px;text-align:center;color:var(--text-muted);}.info-banner.svelte-18cwlk6 {margin-bottom:24px;padding:12px 16px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle);border-radius:8px;font-size:0.8125rem;color:var(--text-muted);line-height:1.4;}.form-section.svelte-18cwlk6 {margin-bottom:24px;}.field-label.svelte-18cwlk6 {display:block;font-size:0.875rem;font-weight:500;margin-bottom:4px;}.status-tag.success.svelte-18cwlk6 {margin-left:8px;font-size:11px;padding:2px 6px;background:rgba(16, 185, 129, 0.15);color:#10b981;border-radius:4px;}.helper-text.svelte-18cwlk6 {font-size:0.75rem;color:var(--text-muted);margin-bottom:8px;line-height:1.5;}.link.svelte-18cwlk6 {color:var(--color-primary);text-decoration:none;}.link.svelte-18cwlk6:hover {text-decoration:underline;}.input-wrapper.svelte-18cwlk6 {position:relative;display:flex;align-items:center;}.input-field.svelte-18cwlk6 {width:100%;padding:10px 14px;padding-right:40px;background:rgba(0, 0, 0, 0.2);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);color:var(--text-primary);font-size:0.875rem;transition:border-color 0.2s;}.input-field.svelte-18cwlk6:focus {outline:none;border-color:var(--color-primary);}.toggle-btn.svelte-18cwlk6 {position:absolute;right:12px;background:transparent;border:none;cursor:pointer;font-size:1.1rem;opacity:0.6;transition:opacity 0.2s;}.toggle-btn.svelte-18cwlk6:hover {opacity:1;}.toggle-card.svelte-18cwlk6 {margin-bottom:24px;padding:16px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);}.toggle-header.svelte-18cwlk6 {display:flex;justify-content:space-between;align-items:center;}.toggle-label.svelte-18cwlk6 {margin:0;font-size:0.875rem;font-weight:600;}.switch.svelte-18cwlk6 {position:relative;width:44px;height:24px;background:rgba(255, 255, 255, 0.2);border-radius:999px;border:none;cursor:pointer;transition:background 0.2s;}.switch.active.svelte-18cwlk6 {background:var(--color-primary, #14b8a6);}.switch-thumb.svelte-18cwlk6 {position:absolute;top:2px;left:2px;width:20px;height:20px;background:white;border-radius:50%;transition:transform 0.2s;}.switch.active.svelte-18cwlk6 .switch-thumb:where(.svelte-18cwlk6) {transform:translateX(20px);}.warning-box.svelte-18cwlk6 {margin-top:12px;padding:8px 12px;background:rgba(245, 158, 11, 0.1);border:1px solid rgba(245, 158, 11, 0.2);border-radius:6px;font-size:11px;color:#fbbf24;line-height:1.4;}.feedback.svelte-18cwlk6 {margin-bottom:16px;padding:10px 14px;border-radius:var(--radius, 12px);font-size:0.875rem;}.feedback.error.svelte-18cwlk6 {background:rgba(239, 68, 68, 0.1);border:1px solid #ef4444;color:#ef4444;}.feedback.success.svelte-18cwlk6 {background:rgba(16, 185, 129, 0.1);border:1px solid #10b981;color:#10b981;}.actions.svelte-18cwlk6 {display:flex;justify-content:flex-end;}.btn-primary.svelte-18cwlk6 {padding:10px 24px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);font-weight:600;border:none;border-radius:var(--radius, 12px);cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-18cwlk6:hover:not(:disabled) {opacity:0.9;box-shadow:0 4px 12px rgba(20, 184, 166, 0.2);}.btn-primary.svelte-18cwlk6:active:not(:disabled) {transform:scale(0.98);}.btn-primary.svelte-18cwlk6:disabled {opacity:0.5;cursor:not-allowed;}.mt-2.svelte-18cwlk6 {margin-top:8px;}"
};
function zi(e, t) {
	Ge(t, !1), Hr(e, Ri);
	let n = di(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(!0), i = /* @__PURE__ */ P(!1), a = /* @__PURE__ */ P(!1), o = /* @__PURE__ */ P(""), s = /* @__PURE__ */ P(""), c = /* @__PURE__ */ P(!1), l = /* @__PURE__ */ P(!1), u = /* @__PURE__ */ P(!1);
	Ar(async () => {
		await d(), F(r, !1);
	});
	async function d() {
		try {
			n();
			let e = await fetch(`${n()}/config`);
			if (e.ok) {
				let t = await e.json();
				F(c, t.token_configured ?? !1), F(u, t.auto_contribute ?? !1), J(c) && F(s, "");
			}
		} catch (e) {
			console.error("[MusicBrainzSettingsCard] Failed to load config:", e);
		}
	}
	async function f() {
		let e = { auto_contribute: J(u) };
		if (J(s).trim()) e.user_token = J(s).trim();
		else if (J(u) && !J(c)) {
			F(o, "A User Token is required to enable auto-contributions.");
			return;
		}
		F(o, ""), F(i, !0), F(a, !1);
		try {
			n();
			let t = await fetch(`${n()}/config`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			});
			if (t.ok) {
				let e = await t.json();
				F(c, e.token_configured ?? J(c)), F(s, ""), F(a, !0), dispatchEvent(new CustomEvent("musicbrainz-config-saved", {
					bubbles: !0,
					composed: !0,
					detail: {
						auto_contribute: J(u),
						token_configured: J(c)
					}
				})), setTimeout(() => F(a, !1), 3e3);
			} else {
				let e = await t.json().catch(() => ({}));
				F(o, e.error || "Failed to save configuration.");
			}
		} catch (e) {
			console.error("[MusicBrainzSettingsCard] Save error:", e), F(o, "Network error while saving. Please try again.");
		} finally {
			F(i, !1);
		}
	}
	var p = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), kt();
		}
	};
	oi();
	var m = Li(), h = R(L(m), 2), g = (e) => {
		Q(e, ji());
	}, _ = (e) => {
		var t = Ii(), n = R(tn(t), 2), r = L(n), d = R(L(r)), p = (e) => {
			Q(e, Mi());
		};
		$(d, (e) => {
			J(c) && e(p);
		}), k(r);
		var m = R(r, 4), h = L(m);
		Xr(h);
		var g = R(h, 2), _ = nn(g, !0);
		k(m), k(n);
		var v = R(n, 2), y = L(v), b = R(L(y), 2);
		k(y);
		var x = R(y, 4), S = (e) => {
			Q(e, Ni());
		};
		$(x, (e) => {
			J(u) && !J(c) && !J(s) && e(S);
		}), k(v);
		var C = R(v, 2), ee = (e) => {
			var t = Pi(), n = nn(t);
			Sn(() => Sr(n, `⚠ ${J(o) ?? ""}`)), Q(e, t);
		};
		$(C, (e) => {
			J(o) && e(ee);
		});
		var te = R(C, 2), ne = (e) => {
			Q(e, Fi());
		};
		$(te, (e) => {
			J(a) && e(ne);
		});
		var re = R(te, 2), w = L(re), T = nn(w, !0);
		k(re), Sn(() => {
			Qr(h, "type", J(l) ? "text" : "password"), Qr(h, "placeholder", J(c) ? "••••••••  (leave blank to keep current)" : "Enter your MusicBrainz user token"), Qr(g, "title", J(l) ? "Hide token" : "Show token"), Qr(g, "aria-label", J(l) ? "Hide token" : "Show token"), Sr(_, J(l) ? "🙈" : "👁️"), Qr(b, "aria-checked", J(u)), Gr(b, 1, `switch ${J(u) ? "active" : ""}`, "svelte-18cwlk6"), w.disabled = J(i), Sr(T, J(i) ? "Saving…" : "Save Settings");
		}), ni(h, () => J(s), (e) => F(s, e)), X("click", g, () => F(l, !J(l))), X("click", b, () => F(u, !J(u))), X("click", w, f), Q(e, t);
	};
	return $(h, (e) => {
		J(r) ? e(g) : e(_, -1);
	}), k(m), Q(e, m), Ke(p);
}
customElements.define("musicbrainz-settings-card", _i(zi, { apiBase: {} }, [], [], { mode: "open" }));

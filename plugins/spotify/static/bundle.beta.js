//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1, t = !1;
function n() {
	t = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
n();
//#endregion
//#region node_modules/svelte/src/constants.js
var r = {}, i = Symbol(), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, _ = Object.isExtensible, v = () => {};
function y(e) {
	return e();
}
function b(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function x() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var S = 1024, C = 2048, w = 4096, ee = 8192, te = 16384, ne = 32768, re = 1 << 25, ie = 65536, ae = 1 << 19, oe = 1 << 20, se = 1 << 25, ce = 65536, le = 1 << 21, ue = 1 << 22, de = 1 << 23, fe = Symbol("$state"), pe = Symbol("legacy props"), me = Symbol(""), he = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), ge = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function _e(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function ve() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function ye(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function be(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function xe() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Se(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Ce() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function we() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Te(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Ee() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function De() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Oe() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function ke() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Ae() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function je(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Me() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var T = !1;
function Ne(e) {
	T = e;
}
var E;
function D(e) {
	if (e === null) throw je(), r;
	return E = e;
}
function Pe() {
	return D(/* @__PURE__ */ I(E));
}
function O(e) {
	if (T) {
		if (/* @__PURE__ */ I(E) !== null) throw je(), r;
		E = e;
	}
}
function Fe(e = 1) {
	if (T) {
		for (var t = e, n = E; t--;) n = /* @__PURE__ */ I(n);
		E = n;
	}
}
function Ie(e = !0) {
	for (var t = 0, n = E;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ I(n);
		e && n.remove(), n = i;
	}
}
function Le(e) {
	if (!e || e.nodeType !== 8) throw je(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Re(e) {
	return e === this.v;
}
function ze(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Be(e) {
	return !ze(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var k = null;
function Ve(e) {
	k = e;
}
function He(e, n = !1, r) {
	k = {
		p: k,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: G,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Ue(e) {
	var t = k, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) gn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, k = t.p, e ?? {};
}
function We() {
	return !t || k !== null && k.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Ge = [];
function Ke() {
	var e = Ge;
	Ge = [], b(e);
}
function qe(e) {
	if (Ge.length === 0 && !st) {
		var t = Ge;
		queueMicrotask(() => {
			t === Ge && Ke();
		});
	}
	Ge.push(e);
}
function Je() {
	for (; Ge.length > 0;) Ke();
}
function Ye(e) {
	var t = G;
	if (t === null) return H.f |= de, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	Xe(e, t);
}
function Xe(e, t) {
	for (; t !== null;) {
		if (t.f & 128) {
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
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var Ze = ~(C | w | S);
function A(e, t) {
	e.f = e.f & Ze | t;
}
function Qe(e) {
	e.f & 512 || e.deps === null ? A(e, S) : A(e, w);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function $e(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= ce, $e(t.deps));
}
function et(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), $e(e.deps), A(e, S);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var tt = !1, nt = !1;
function rt(e) {
	var t = nt;
	try {
		return nt = !1, [e(), nt];
	} finally {
		nt = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var it = /* @__PURE__ */ new Set(), j = null, at = null, M = null, ot = null, st = !1, ct = !1, lt = null, ut = null, dt = 0, ft = 1, pt = class t {
	id = ft++;
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#e = /* @__PURE__ */ new Set();
	#t = /* @__PURE__ */ new Set();
	#n = /* @__PURE__ */ new Set();
	#r = /* @__PURE__ */ new Map();
	#i = /* @__PURE__ */ new Map();
	#a = null;
	#o = [];
	#s = [];
	#c = /* @__PURE__ */ new Set();
	#l = /* @__PURE__ */ new Set();
	#u = /* @__PURE__ */ new Map();
	#d = /* @__PURE__ */ new Set();
	is_fork = !1;
	#f = !1;
	#p = /* @__PURE__ */ new Set();
	#m() {
		return this.is_fork || this.#i.size > 0;
	}
	#h() {
		for (let n of this.#p) for (let r of n.#i.keys()) {
			for (var e = !1, t = r; t.parent !== null;) {
				if (this.#u.has(t)) {
					e = !0;
					break;
				}
				t = t.parent;
			}
			if (!e) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#u.has(e) || this.#u.set(e, {
			d: [],
			m: []
		}), this.#d.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#u.get(e);
		if (n) {
			this.#u.delete(e);
			for (var r of n.d) A(r, C), t(r);
			for (r of n.m) A(r, w), t(r);
		}
		this.#d.add(e);
	}
	#g() {
		if (dt++ > 1e3 && (it.delete(this), ht()), !this.#m()) {
			for (let e of this.#c) this.#l.delete(e), A(e, C), this.schedule(e);
			for (let e of this.#l) A(e, w), this.schedule(e);
		}
		let n = this.#o;
		this.#o = [], this.apply();
		var r = lt = [], i = [], a = ut = [];
		for (let e of n) try {
			this.#_(e, r, i);
		} catch (t) {
			throw St(e), t;
		}
		if (j = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (lt = null, ut = null, this.#m() || this.#h()) {
			this.#v(i), this.#v(r);
			for (let [e, t] of this.#u) xt(e, t);
		} else {
			this.#r.size === 0 && it.delete(this), this.#c.clear(), this.#l.clear();
			for (let e of this.#e) e(this);
			this.#e.clear(), at = this, _t(i), _t(r), at = null, this.#a?.resolve();
		}
		var s = j;
		if (this.#o.length > 0) {
			let e = s ??= this;
			e.#o.push(...this.#o.filter((t) => !e.#o.includes(t)));
		}
		s !== null && (it.add(s), s.#g()), e && !it.has(this) && this.#y();
	}
	#_(t, n, r) {
		t.f ^= S;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#u.has(i)) && i.fn !== null) {
				o ? i.f ^= S : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : qn(i) && (a & 16 && this.#l.add(i), Qn(i));
				var s = i.first;
				if (s !== null) {
					i = s;
					continue;
				}
			}
			for (; i !== null;) {
				var c = i.next;
				if (c !== null) {
					i = c;
					break;
				}
				i = i.parent;
			}
		}
	}
	#v(e) {
		for (var t = 0; t < e.length; t += 1) et(e[t], this.#c, this.#l);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), M?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		j = this;
	}
	deactivate() {
		j = null, M = null;
	}
	flush() {
		try {
			ct = !0, j = this, this.#g();
		} finally {
			dt = 0, ot = null, lt = null, ut = null, ct = !1, j = null, M = null, Bt.clear();
		}
	}
	discard() {
		for (let e of this.#t) e(this);
		this.#t.clear(), this.#n.clear(), it.delete(this);
	}
	register_created_effect(e) {
		this.#s.push(e);
	}
	#y() {
		for (let l of it) {
			var e = l.id < this.id, t = [];
			for (let [r, [i, a]] of this.current) {
				if (l.current.has(r)) {
					var n = l.current.get(r)[0];
					if (e && i !== n) l.current.set(r, [i, a]);
					else continue;
				}
				t.push(r);
			}
			var r = [...l.current.keys()].filter((e) => !this.current.has(e));
			if (r.length === 0) e && l.discard();
			else if (t.length > 0) {
				if (e) for (let e of this.#d) l.unskip_effect(e, (e) => {
					e.f & 4194320 ? l.schedule(e) : l.#v([e]);
				});
				l.activate();
				var i = /* @__PURE__ */ new Set(), a = /* @__PURE__ */ new Map();
				for (var o of t) vt(o, r, i, a);
				a = /* @__PURE__ */ new Map();
				var s = [...l.current.keys()].filter((e) => this.current.has(e) ? this.current.get(e)[0] !== e : !0);
				for (let e of this.#s) !(e.f & 155648) && yt(e, s, a) && (e.f & 4194320 ? (A(e, C), l.schedule(e)) : l.#c.add(e));
				if (l.#o.length > 0) {
					l.apply();
					for (var c of l.#o) l.#_(c, [], []);
					l.#o = [];
				}
				l.deactivate();
			}
		}
		for (let e of it) e.#p.has(this) && (e.#p.delete(this), e.#p.size === 0 && !e.#m() && (e.activate(), e.#g()));
	}
	increment(e, t) {
		let n = this.#r.get(t) ?? 0;
		if (this.#r.set(t, n + 1), e) {
			let e = this.#i.get(t) ?? 0;
			this.#i.set(t, e + 1);
		}
	}
	decrement(e, t, n) {
		let r = this.#r.get(t) ?? 0;
		if (r === 1 ? this.#r.delete(t) : this.#r.set(t, r - 1), e) {
			let e = this.#i.get(t) ?? 0;
			e === 1 ? this.#i.delete(t) : this.#i.set(t, e - 1);
		}
		this.#f || n || (this.#f = !0, qe(() => {
			this.#f = !1, this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#c.add(t);
		for (let e of t) this.#l.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#e.add(e);
	}
	ondiscard(e) {
		this.#t.add(e);
	}
	on_fork_commit(e) {
		this.#n.add(e);
	}
	run_fork_commit_callbacks() {
		for (let e of this.#n) e(this);
		this.#n.clear();
	}
	settled() {
		return (this.#a ??= x()).promise;
	}
	static ensure() {
		if (j === null) {
			let e = j = new t();
			ct || (it.add(j), st || qe(() => {
				j === e && e.flush();
			}));
		}
		return j;
	}
	apply() {
		if (!e || !this.is_fork && it.size === 1) {
			M = null;
			return;
		}
		M = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) M.set(e, t);
		for (let e of it) if (!(e === this || e.is_fork)) {
			var t = !1, n = !1;
			if (e.id < this.id) for (let [r, [, i]] of e.current) i || (t ||= this.current.has(r), n ||= !this.current.has(r));
			if (t && n) this.#p.add(e);
			else for (let [t, n] of e.previous) M.has(t) || M.set(t, n);
		}
	}
	schedule(t) {
		if (ot = t, t.b?.is_pending && t.f & 16777228 && !(t.f & 32768)) {
			t.b.defer_effect(t);
			return;
		}
		for (var n = t; n.parent !== null;) {
			n = n.parent;
			var r = n.f;
			if (lt !== null && n === G && (e || (H === null || !(H.f & 2)) && !tt)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= S;
			}
		}
		this.#o.push(n);
	}
};
function mt(e) {
	var t = st;
	st = !0;
	try {
		var n;
		for (e && (j !== null && !j.is_fork && j.flush(), n = e());;) {
			if (Je(), j === null) return n;
			j.flush();
		}
	} finally {
		st = t;
	}
}
function ht() {
	try {
		Ce();
	} catch (e) {
		Xe(e, ot);
	}
}
var gt = null;
function _t(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && qn(r) && (gt = /* @__PURE__ */ new Set(), Qn(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && kn(r), gt?.size > 0)) {
				Bt.clear();
				for (let e of gt) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) gt.has(n) && (gt.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || Qn(n);
					}
				}
				gt.clear();
			}
		}
		gt = null;
	}
}
function vt(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? vt(i, t, n, r) : e & 4194320 && !(e & 2048) && yt(i, t, r) && (A(i, C), bt(i));
	}
}
function yt(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && yt(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function bt(e) {
	j.schedule(e);
}
function xt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), A(e, S);
		for (var n = e.first; n !== null;) xt(n, t), n = n.next;
	}
}
function St(e) {
	A(e, S);
	for (var t = e.first; t !== null;) St(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function Ct(e) {
	let t = 0, n = Ht(0), r;
	return () => {
		pn() && (X(n), Sn(() => (t === 0 && (r = Z(() => e(() => Kt(n)))), t += 1, () => {
			qe(() => {
				--t, t === 0 && (r?.(), r = void 0, Kt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var wt = ie | ae;
function Tt(e, t, n, r) {
	new Et(e, t, n, r);
}
var Et = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = T ? E : null;
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
	#h = Ct(() => (this.#m = Ht(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = wn(() => {
			if (T) {
				let e = this.#t;
				Pe();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, wt), T && (this.#e = E);
	}
	#g() {
		try {
			this.#a = B(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = B(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = B(() => e(this.#e)), qe(() => {
			var e = this.#c = document.createDocumentFragment(), t = F();
			e.append(t), this.#a = this.#x(() => B(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, An(this.#o, () => {
				this.#o = null;
			}), this.#b(j));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = B(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Pn(this.#a, e);
				let t = this.#n.pending;
				this.#o = B(() => t(this.#e));
			} else this.#b(j);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		et(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = G, n = H, r = k;
		zn(this.#i), W(this.#i), Ve(this.#i.ctx);
		try {
			return pt.ensure(), e();
		} catch (e) {
			return Ye(e), null;
		} finally {
			zn(t), W(n), Ve(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && An(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, qe(() => {
			this.#d = !1, this.#m && Wt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), X(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		j?.is_fork ? (this.#a && j.skip_effect(this.#a), this.#o && j.skip_effect(this.#o), this.#s && j.skip_effect(this.#s), j.on_fork_commit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), T && (D(this.#t), Fe(), D(Ie()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Me();
				return;
			}
			r = !0, i && ke(), this.#s !== null && An(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				Xe(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return B(() => {
						var t = G;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return Xe(e, this.#i.parent), null;
				}
			}));
		};
		qe(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				Xe(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => Xe(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function Dt(e, t, n, r) {
	let i = We() ? jt : Nt;
	var a = e.filter((e) => !e.settled);
	if (n.length === 0 && a.length === 0) {
		r(t.map(i));
		return;
	}
	var o = G, s = Ot(), c = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function l(e) {
		s();
		try {
			r(e);
		} catch (e) {
			o.f & 16384 || Xe(e, o);
		}
		kt();
	}
	if (n.length === 0) {
		c.then(() => l(t.map(i)));
		return;
	}
	var u = At();
	function d() {
		Promise.all(n.map((e) => /* @__PURE__ */ Mt(e))).then((e) => l([...t.map(i), ...e])).catch((e) => Xe(e, o)).finally(() => u());
	}
	c ? c.then(() => {
		s(), d(), kt();
	}) : d();
}
function Ot() {
	var e = G, t = H, n = k, r = j;
	return function(i = !0) {
		zn(e), W(t), Ve(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function kt(e = !0) {
	zn(null), W(null), Ve(null), e && j?.deactivate();
}
function At() {
	var e = G, t = e.b, n = j, r = t.is_rendered();
	return t.update_pending_count(1, n), n.increment(r, e), (i = !1) => {
		t.update_pending_count(-1, n), n.decrement(r, e, i);
	};
}
/* @__NO_SIDE_EFFECTS__ */
function jt(e) {
	var t = 2 | C;
	return G !== null && (G.f |= ae), {
		ctx: k,
		deps: null,
		effects: null,
		equals: Re,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: G,
		ac: null
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Mt(e, t, n) {
	let r = G;
	r === null && ve();
	var a = void 0, o = Ht(i), s = !H, c = /* @__PURE__ */ new Map();
	return xn(() => {
		var t = G, n = x();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, n.reject).finally(kt);
		} catch (e) {
			n.reject(e), kt();
		}
		var i = j;
		if (s) {
			if (t.f & 32768) var l = At();
			if (r.b.is_rendered()) c.get(i)?.reject(he), c.delete(i);
			else {
				for (let e of c.values()) e.reject(he);
				c.clear();
			}
			c.set(i, n);
		}
		let u = (e, n = void 0) => {
			if (l && l(n === he), !(n === he || t.f & 16384)) {
				if (i.activate(), n) o.f |= de, Wt(o, n);
				else {
					o.f & 8388608 && (o.f ^= de), Wt(o, e);
					for (let [e, t] of c) {
						if (c.delete(e), e === i) break;
						t.reject(he);
					}
				}
				i.deactivate();
			}
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), mn(() => {
		for (let e of c.values()) e.reject(he);
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
/* @__NO_SIDE_EFFECTS__ */
function Nt(e) {
	let t = /* @__PURE__ */ jt(e);
	return t.equals = Be, t;
}
function Pt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function Ft(e) {
	var t, n = G, r = e.parent;
	if (!Ln && r !== null && r.f & 24576) return Ae(), e.v;
	zn(r);
	try {
		e.f &= ~ce, Pt(e), t = Yn(e);
	} finally {
		zn(n);
	}
	return t;
}
function It(e) {
	var t = Ft(e);
	if (!e.equals(t) && (e.wv = Kn(), (!j?.is_fork || e.deps === null) && (j === null ? e.v = t : j.capture(e, t, !0), e.deps === null))) {
		A(e, S);
		return;
	}
	Ln || (M === null ? Qe(e) : (pn() || j?.is_fork) && M.set(e, t));
}
function Lt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(he), t.teardown = v, t.ac = null, Zn(t, 0), En(t));
}
function Rt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && Qn(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var zt = /* @__PURE__ */ new Set(), Bt = /* @__PURE__ */ new Map(), Vt = !1;
function Ht(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Re,
		rv: 0,
		wv: 0
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Ut(e, t) {
	let n = Ht(e, t);
	return Bn(n), n;
}
/* @__NO_SIDE_EFFECTS__ */
function N(e, n = !1, r = !0) {
	let i = Ht(e);
	return n || (i.equals = Be), t && r && k !== null && k.l !== null && (k.l.s ??= []).push(i), i;
}
function P(e, t, n = !1) {
	return H !== null && (!U || H.f & 131072) && We() && H.f & 4325394 && (K === null || !c.call(K, e)) && Oe(), Wt(e, n ? Jt(t) : t, ut);
}
function Wt(e, t, n = null) {
	if (!e.equals(t)) {
		Bt.set(e, Ln ? t : e.v);
		var r = pt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Ft(t), M === null && Qe(t);
		}
		e.wv = Kn(), qt(e, C, n), We() && G !== null && G.f & 1024 && !(G.f & 96) && (Y === null ? Vn([e]) : Y.push(e)), !r.is_fork && zt.size > 0 && !Vt && Gt();
	}
	return t;
}
function Gt() {
	Vt = !1;
	for (let e of zt) e.f & 1024 && A(e, w), qn(e) && Qn(e);
	zt.clear();
}
function Kt(e) {
	P(e, e.v + 1);
}
function qt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = We(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === G)) {
			var l = (c & C) === 0;
			if (l && A(s, t), c & 2) {
				var u = s;
				M?.delete(u), c & 65536 || (c & 512 && (s.f |= ce), qt(u, w, n));
			} else if (l) {
				var d = s;
				c & 16 && gt !== null && gt.add(d), n === null ? bt(d) : n.push(d);
			}
		}
	}
}
function Jt(e) {
	if (typeof e != "object" || !e || fe in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ Ut(0), s = null, c = Wn, l = (e) => {
		if (Wn === c) return e();
		var t = H, n = Wn;
		W(null), Gn(c);
		var r = e();
		return W(t), Gn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ Ut(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && Ee();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Ut(r.value, s);
				return n.set(t, e), e;
			}) : P(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Ut(i, s));
					n.set(t, e), Kt(a);
				}
			} else P(r, i), Kt(a);
			return !0;
		},
		get(t, r, a) {
			if (r === fe) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ Ut(Jt(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
				var u = X(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = X(a));
			} else if (r === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== i) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === fe) return !0;
			var r = n.get(t), a = r !== void 0 && r.v !== i || Reflect.has(e, t);
			return (r !== void 0 || G !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ Ut(a ? Jt(e[t]) : i, s)), n.set(t, r)), X(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Ut(i, s)), n.set(p + "", m)) : P(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Ut(void 0, s)), P(u, Jt(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => Jt(o));
				P(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && P(_, v + 1);
				}
				Kt(a);
			}
			return !0;
		},
		ownKeys(e) {
			X(a);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== i;
			});
			for (var [r, o] of n) o.v !== i && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			De();
		}
	});
}
var Yt, Xt, Zt, Qt;
function $t() {
	if (Yt === void 0) {
		Yt = window, Xt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Zt = f(t, "firstChild").get, Qt = f(t, "nextSibling").get, _(e) && (e.__click = void 0, e.__className = void 0, e.__attributes = null, e.__style = void 0, e.__e = void 0), _(n) && (n.__t = void 0);
	}
}
function F(e = "") {
	return document.createTextNode(e);
}
/* @__NO_SIDE_EFFECTS__ */
function en(e) {
	return Zt.call(e);
}
/* @__NO_SIDE_EFFECTS__ */
function I(e) {
	return Qt.call(e);
}
function L(e, t) {
	if (!T) return /* @__PURE__ */ en(e);
	var n = /* @__PURE__ */ en(E);
	if (n === null) n = E.appendChild(F());
	else if (t && n.nodeType !== 3) {
		var r = F();
		return n?.before(r), D(r), r;
	}
	return t && on(n), D(n), n;
}
function tn(e, t = !1) {
	if (!T) {
		var n = /* @__PURE__ */ en(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ I(n) : n;
	}
	if (t) {
		if (E?.nodeType !== 3) {
			var r = F();
			return E?.before(r), D(r), r;
		}
		on(E);
	}
	return E;
}
function R(e, t = 1, n = !1) {
	let r = T ? E : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ I(r);
	if (!T) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = F();
			return r === null ? i?.after(a) : r.before(a), D(a), a;
		}
		on(r);
	}
	return D(r), r;
}
function nn(e) {
	e.textContent = "";
}
function rn() {
	return !e || gt !== null ? !1 : (G.f & ne) !== 0;
}
function an(e, t, n) {
	let r = n ? { is: n } : void 0;
	return document.createElementNS(t ?? "http://www.w3.org/1999/xhtml", e, r);
}
function on(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var sn = !1;
function cn() {
	sn || (sn = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t.__on_r?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function ln(e) {
	var t = H, n = G;
	W(null), zn(null);
	try {
		return e();
	} finally {
		W(t), zn(n);
	}
}
function un(e, t, n, r = n) {
	e.addEventListener(t, () => ln(n));
	let i = e.__on_r;
	i ? e.__on_r = () => {
		i(), r(!0);
	} : e.__on_r = () => r(!0), cn();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function dn(e) {
	G === null && (H === null && Se(e), xe()), Ln && be(e);
}
function fn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function z(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= ee);
	var r = {
		ctx: k,
		deps: null,
		nodes: null,
		f: e | C | 512,
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
	j?.register_created_effect(r);
	var i = r;
	if (e & 4) lt === null ? pt.ensure().schedule(r) : lt.push(r);
	else if (t !== null) {
		try {
			Qn(r);
		} catch (e) {
			throw V(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= ie));
	}
	if (i !== null && (i.parent = n, n !== null && fn(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function pn() {
	return H !== null && !U;
}
function mn(e) {
	let t = z(8, null);
	return A(t, S), t.teardown = e, t;
}
function hn(e) {
	dn("$effect");
	var t = G.f;
	if (!H && t & 32 && !(t & 32768)) {
		var n = k;
		(n.e ??= []).push(e);
	} else return gn(e);
}
function gn(e) {
	return z(4 | oe, e);
}
function _n(e) {
	return dn("$effect.pre"), z(8 | oe, e);
}
function vn(e) {
	pt.ensure();
	let t = z(64 | ae, e);
	return () => {
		V(t);
	};
}
function yn(e) {
	pt.ensure();
	let t = z(64 | ae, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? An(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function bn(e) {
	return z(4, e);
}
function xn(e) {
	return z(ue | ae, e);
}
function Sn(e, t = 0) {
	return z(8 | t, e);
}
function Cn(e, t = [], n = [], r = []) {
	Dt(r, t, n, (t) => {
		z(8, () => e(...t.map(X)));
	});
}
function wn(e, t = 0) {
	return z(16 | t, e);
}
function B(e) {
	return z(32 | ae, e);
}
function Tn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = Ln, n = H;
		Rn(!0), W(null);
		try {
			t.call(null);
		} finally {
			Rn(e), W(n);
		}
	}
}
function En(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && ln(() => {
			e.abort(he);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function Dn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (On(e.nodes.start, e.nodes.end), n = !0), A(e, re), En(e, t && !n), Zn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Tn(e), e.f ^= re, e.f |= te;
	var i = e.parent;
	i !== null && i.first !== null && kn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function On(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ I(e);
		e.remove(), e = n;
	}
}
function kn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function An(e, t, n = !0) {
	var r = [];
	jn(e, r, !0);
	var i = () => {
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function jn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ee;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				jn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Mn(e) {
	Nn(e, !0);
}
function Nn(e, t) {
	if (e.f & 8192) {
		e.f ^= ee, e.f & 1024 || (A(e, C), pt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Nn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Pn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ I(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Fn = null, In = !1, Ln = !1;
function Rn(e) {
	Ln = e;
}
var H = null, U = !1;
function W(e) {
	H = e;
}
var G = null;
function zn(e) {
	G = e;
}
var K = null;
function Bn(t) {
	H !== null && (!e || H.f & 2) && (K === null ? K = [t] : K.push(t));
}
var q = null, J = 0, Y = null;
function Vn(e) {
	Y = e;
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
	if (t & 2 && (e.f &= ~ce), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (qn(a) && It(a), a.wv > e.wv) return !0;
		}
		t & 512 && M === null && A(e, S);
	}
	return !1;
}
function Jn(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && K !== null && c.call(K, t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? Jn(o, n, !1) : n === o && (r ? A(o, C) : o.f & 1024 && A(o, w), bt(o));
	}
}
function Yn(e) {
	var t = q, n = J, r = Y, i = H, a = K, o = k, s = U, c = Wn, l = e.f;
	q = null, J = 0, Y = null, H = l & 96 ? null : e, K = null, Ve(e.ctx), U = !1, Wn = ++Un, e.ac !== null && (ln(() => {
		e.ac.abort(he);
	}), e.ac = null);
	try {
		e.f |= le;
		var u = e.fn, d = u();
		e.f |= ne;
		var f = e.deps, p = j?.is_fork;
		if (q !== null) {
			var m;
			if (p || Zn(e, J), f !== null && J > 0) for (f.length = J + q.length, m = 0; m < q.length; m++) f[J + m] = q[m];
			else e.deps = f = q;
			if (pn() && e.f & 512) for (m = J; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && J < f.length && (Zn(e, J), f.length = J);
		if (We() && Y !== null && !U && f !== null && !(e.f & 6146)) for (m = 0; m < Y.length; m++) Jn(Y[m], e);
		if (i !== null && i !== e) {
			if (Un++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Un;
			if (t !== null) for (let e of t) e.rv = Un;
			Y !== null && (r === null ? r = Y : r.push(...Y));
		}
		return e.f & 8388608 && (e.f ^= de), d;
	} catch (e) {
		return Ye(e);
	} finally {
		e.f ^= le, q = t, J = n, Y = r, H = i, K = a, Ve(o), U = s, Wn = c;
	}
}
function Xn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (q === null || !c.call(q, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~ce), o.v !== i && Qe(o), Lt(o), Zn(o, 0);
	}
}
function Zn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Xn(e, n[r]);
}
function Qn(e) {
	var t = e.f;
	if (!(t & 16384)) {
		A(e, S);
		var n = G, r = In;
		G = e, In = !0;
		try {
			t & 16777232 ? Dn(e) : En(e), Tn(e);
			var i = Yn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Hn;
		} finally {
			In = r, G = n;
		}
	}
}
async function $n() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), mt();
}
function X(e) {
	var t = (e.f & 2) != 0;
	if (Fn?.add(e), H !== null && !U && !(G !== null && G.f & 16384) && (K === null || !c.call(K, e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < Un && (e.rv = Un, q === null && n !== null && n[J] === e ? J++ : q === null ? q = [e] : q.push(e));
		else {
			(H.deps ??= []).push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : c.call(r, H) || r.push(H);
		}
	}
	if (Ln && Bt.has(e)) return Bt.get(e);
	if (t) {
		var i = e;
		if (Ln) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || tr(i)) && (a = Ft(i)), Bt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !U && H !== null && (In || (H.f & 512) != 0), s = (i.f & ne) === 0;
		qn(i) && (o && (i.f |= 512), It(i)), o && !s && (Rt(i), er(i));
	}
	if (M?.has(e)) return M.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function er(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Rt(t), er(t));
}
function tr(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Bt.has(t) || t.f & 2 && tr(t)) return !0;
	return !1;
}
function Z(e) {
	var t = U;
	try {
		return U = !0, e();
	} finally {
		U = t;
	}
}
function nr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (fe in e) rr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && fe in n && rr(n);
		}
	}
}
function rr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			rr(e[n], t);
		} catch {}
		let n = g(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = p(n);
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
var ir = Symbol("events"), ar = /* @__PURE__ */ new Set(), or = /* @__PURE__ */ new Set();
function sr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || ur.call(t, e), !e.cancelBubble) return ln(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? qe(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function cr(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = sr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && mn(() => {
		t.removeEventListener(e, o, a);
	});
}
var lr = null;
function ur(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	lr = e;
	var o = 0, s = lr === e && e[ir];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[ir] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		d(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var u = H, f = G;
		W(null), zn(null);
		try {
			for (var p, m = []; a !== null;) {
				var h = a.assignedSlot || a.parentNode || a.host || null;
				try {
					var g = a[ir]?.[r];
					g != null && (!a.disabled || e.target === a) && g.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble || h === t || h === null) break;
				a = h;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[ir] = t, delete e.currentTarget, W(u), zn(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var dr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function fr(e) {
	return dr?.createHTML(e) ?? e;
}
function pr(e) {
	var t = an("template");
	return t.innerHTML = fr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function mr(e, t) {
	var n = G;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/* @__NO_SIDE_EFFECTS__ */
function Q(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (T) return mr(E, null), E;
		i === void 0 && (i = pr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ en(i)));
		var t = r || Xt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ en(t), s = t.lastChild;
			mr(o, s);
		} else mr(t, t);
		return t;
	};
}
function $(e, t) {
	if (T) {
		var n = G;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = E), Pe();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var hr = ["touchstart", "touchmove"];
function gr(e) {
	return hr.includes(e);
}
function _r(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e.__t ??= e.nodeValue) && (e.__t = n, e.nodeValue = `${n}`);
}
function vr(e, t) {
	return xr(e, t);
}
function yr(e, t) {
	$t(), t.intro = t.intro ?? !1;
	let n = t.target, i = T, a = E;
	try {
		for (var o = /* @__PURE__ */ en(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ I(o);
		if (!o) throw r;
		Ne(!0), D(o);
		let i = xr(e, {
			...t,
			anchor: o
		});
		return Ne(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && we(), $t(), nn(n), Ne(!1), vr(e, t);
	} finally {
		Ne(i), D(a);
	}
}
var br = /* @__PURE__ */ new Map();
function xr(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	$t();
	var u = void 0, d = yn(() => {
		var s = n ?? t.appendChild(F());
		Tt(s, { pending: () => {} }, (t) => {
			He({});
			var n = k;
			if (o && (n.c = o), a && (i.$$events = a), T && mr(t, null), u = e(t, i) || {}, T && (G.nodes.end = E, E === null || E.nodeType !== 8 || E.data !== "]")) throw je(), r;
			Ue();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = gr(r);
					for (let e of [t, document]) {
						var a = br.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), br.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, ur, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(ar)), or.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = br.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, ur), r.delete(e), r.size === 0 && br.delete(n)) : r.set(e, i);
			}
			or.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return Sr.set(u, d), u;
}
var Sr = /* @__PURE__ */ new WeakMap();
function Cr(e, t) {
	let n = Sr.get(e);
	return n ? (Sr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var wr = class {
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
				r && (this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
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
						Pn(r, t), t.append(F()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), An(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = j, r = rn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = F();
			i.append(a), this.#n.set(e, {
				effect: B(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, B(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else T && (this.anchor = E), this.#a(n);
	}
};
function Tr(e) {
	k === null && _e("onMount"), t && k.l !== null ? Er(k).m.push(e) : hn(() => {
		let t = Z(e);
		if (typeof t == "function") return t;
	});
}
function Er(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Dr(e, t, n = !1) {
	var r;
	T && (r = E, Pe());
	var i = new wr(e), a = n ? ie : 0;
	function o(e, t) {
		if (T) {
			var n = Le(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Ie();
				D(a), i.anchor = a, Ne(!1), i.ensure(e, t), Ne(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	wn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/each.js
function Or(e, t) {
	return t;
}
function kr(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		An(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					Ar(e, l(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var c = r.length === 0 && n !== null;
		if (c) {
			var u = n, d = u.parentNode;
			nn(d), d.append(u), e.items.clear();
		}
		Ar(e, t, !c);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function Ar(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= se, Pn(a, document.createDocumentFragment())) : V(t[i], n);
	}
}
var jr;
function Mr(e, t, n, r, i, a = null) {
	var s = e, c = /* @__PURE__ */ new Map();
	if (t & 4) {
		var u = e;
		s = T ? D(/* @__PURE__ */ en(u)) : u.appendChild(F());
	}
	T && Pe();
	var d = null, f = /* @__PURE__ */ Nt(() => {
		var e = n();
		return o(e) ? e : e == null ? [] : l(e);
	}), p, m = /* @__PURE__ */ new Map(), h = !0;
	function g(e) {
		v.effect.f & 16384 || (v.pending.delete(e), v.fallback = d, Pr(v, p, s, t, r), d !== null && (p.length === 0 ? d.f & 33554432 ? (d.f ^= se, Ir(d, null, s)) : Mn(d) : An(d, () => {
			d = null;
		})));
	}
	function _(e) {
		v.pending.delete(e);
	}
	var v = {
		effect: wn(() => {
			p = X(f);
			var e = p.length;
			let o = !1;
			T && Le(s) === "[!" != (e === 0) && (s = Ie(), D(s), Ne(!1), o = !0);
			for (var l = /* @__PURE__ */ new Set(), u = j, v = rn(), y = 0; y < e; y += 1) {
				T && E.nodeType === 8 && E.data === "]" && (s = E, o = !0, Ne(!1));
				var b = p[y], x = r(b, y), S = h ? null : c.get(x);
				S ? (S.v && Wt(S.v, b), S.i && Wt(S.i, y), v && u.unskip_effect(S.e)) : (S = Fr(c, h ? s : jr ??= F(), b, x, y, i, t, n), h || (S.e.f |= se), c.set(x, S)), l.add(x);
			}
			if (e === 0 && a && !d && (h ? d = B(() => a(s)) : (d = B(() => a(jr ??= F())), d.f |= se)), e > l.size && ye("", "", ""), T && e > 0 && D(Ie()), !h) if (m.set(u, l), v) {
				for (let [e, t] of c) l.has(e) || u.skip_effect(t.e);
				u.oncommit(g), u.ondiscard(_);
			} else g(u);
			o && Ne(!0), X(f);
		}),
		flags: t,
		items: c,
		pending: m,
		outrogroups: null,
		fallback: d
	};
	h = !1, T && (s = E);
}
function Nr(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function Pr(e, t, n, r, i) {
	var a = (r & 8) != 0, o = t.length, s = e.items, c = Nr(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (Mn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) if (_.f ^= se, _ === c) Ir(_, null, n);
		else {
			var y = d ? d.next : c;
			_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), Lr(e, d, _), Lr(e, _, y), Ir(_, y, n), d = _, p = [], m = [], c = Nr(d.next);
			continue;
		}
		if (_ !== c) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) Ir(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					Lr(e, S.prev, C.next), Lr(e, d, S), Lr(e, C, b), c = b, d = C, --v, p = [], m = [];
				} else u.delete(_), Ir(_, c, n), Lr(e, _.prev, _.next), Lr(e, _, d === null ? e.effect.first : d.next), Lr(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; c !== null && c !== _;) (u ??= /* @__PURE__ */ new Set()).add(c), m.push(c), c = Nr(c.next);
			if (c === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, c = Nr(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (Ar(e, l(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (c !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; c !== null;) !(c.f & 8192) && c !== e.fallback && w.push(c), c = Nr(c.next);
		var ee = w.length;
		if (ee > 0) {
			var te = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.fix();
			}
			kr(e, w, te);
		}
	}
	a && qe(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function Fr(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Ht(n) : /* @__PURE__ */ N(n, !1, !1) : null, l = o & 2 ? Ht(i) : null;
	return {
		v: c,
		i: l,
		e: B(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function Ir(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ I(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function Lr(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Rr(e, t) {
	bn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = an("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/shared/attributes.js
var zr = [..." 	\n\r\f\xA0\v﻿"];
function Br(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || zr.includes(r[o - 1])) && (s === r.length || zr.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/class.js
function Vr(e, t, n, r, i, a) {
	var o = e.__className;
	if (T || o !== n || o === void 0) {
		var s = Br(n, r, a);
		(!T || s !== e.getAttribute("class")) && (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e.__className = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Hr = Symbol("is custom element"), Ur = Symbol("is html"), Wr = ge ? "link" : "LINK";
function Gr(e) {
	if (T) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Kr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Kr(e, "checked", null), e.checked = r;
				}
			}
		};
		e.__on_r = n, qe(n), cn();
	}
}
function Kr(e, t, n, r) {
	var i = qr(e);
	T && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Wr) || i[t] !== (i[t] = n) && (t === "loading" && (e[me] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Yr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function qr(e) {
	return e.__attributes ??= {
		[Hr]: e.nodeName.includes("-"),
		[Ur]: e.namespaceURI === a
	};
}
var Jr = /* @__PURE__ */ new Map();
function Yr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Jr.get(t);
	if (n) return n;
	Jr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Xr(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	un(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = Zr(t) ? Qr(a) : a, r(a), j !== null && i.add(j), await $n(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (T && t.defaultValue !== t.value || Z(n) == null && t.value) && (r(Zr(t) ? Qr(t.value) : t.value), j !== null && i.add(j)), Sn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? at : j;
			if (i.has(a)) return;
		}
		Zr(t) && r === Qr(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function Zr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Qr(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function $r(e = !1) {
	let t = k, n = t.l.u;
	if (!n) return;
	let r = () => nr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ jt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => X(i);
	}
	n.b.length && _n(() => {
		ei(t, r), b(n.b);
	}), hn(() => {
		let e = Z(() => n.m.map(y));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && hn(() => {
		ei(t, r), b(n.a);
	});
}
function ei(e, t) {
	if (e.l.s) for (let t of e.l.s) X(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function ti(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = () => (l && (l = !1, c = s ? Z(i) : i), c);
	let d;
	if (o) {
		var p = fe in e || pe in e;
		d = f(e, n)?.set ?? (p && n in e ? (t) => e[n] = t : void 0);
	}
	var m, h = !1;
	o ? [m, h] = rt(() => e[n]) : m = e[n], m === void 0 && i !== void 0 && (m = u(), d && (a && Te(n), d(m)));
	var g = a ? () => {
		var t = e[n];
		return t === void 0 ? u() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return g;
	if (d) {
		var _ = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || _ || h) && d(t ? g() : e), e) : g();
		});
	}
	var v = !1, y = (r & 1 ? jt : Nt)(() => (v = !1, g()));
	o && X(y);
	var b = G;
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
function ni(e) {
	return new ri(e);
}
var ri = class {
	#e;
	#t;
	constructor(t) {
		var n = /* @__PURE__ */ new Map(), r = (e, t) => {
			var r = /* @__PURE__ */ N(t, !1, !1);
			return n.set(e, r), r;
		};
		let i = new Proxy({
			...t.props || {},
			$$events: {}
		}, {
			get(e, t) {
				return X(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === pe ? !0 : (X(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
			},
			set(e, t, i) {
				return P(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? yr : vr)(t.component, {
			target: t.target,
			anchor: t.anchor,
			props: i,
			context: t.context,
			intro: t.intro ?? !1,
			recover: t.recover,
			transformError: t.transformError
		}), !e && (!t?.props?.$$host || t.sync === !1) && mt(), this.#e = i.$$events;
		for (let e of Object.keys(this.#t)) e === "$set" || e === "$destroy" || e === "$on" || d(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(i, e);
		}, this.#t.$destroy = () => {
			Cr(this.#t);
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
}, ii;
typeof HTMLElement == "function" && (ii = class extends HTMLElement {
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
			let t = {}, n = oi(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = ai(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = ni({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = vn(() => {
				Sn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = ai(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = ai(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return u(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function ai(e, t, n, r) {
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
function oi(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function si(e, t, n, r, i, a) {
	let o = class extends ii {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return u(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return u(t).forEach((e) => {
		d(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = ai(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (f(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		d(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region SpotifyCard.svelte
var ci = /* @__PURE__ */ Q("<div class=\"loading svelte-16m7f8c\">Loading...</div>"), li = /* @__PURE__ */ Q("<div class=\"form-group svelte-16m7f8c\"><label class=\"svelte-16m7f8c\"><span class=\"label-text svelte-16m7f8c\">Client ID</span> <input type=\"text\" placeholder=\"Enter Spotify Client ID\" class=\"input svelte-16m7f8c\"/></label> <label class=\"svelte-16m7f8c\"><span class=\"label-text svelte-16m7f8c\">Client Secret</span> <input type=\"password\" placeholder=\"Enter Spotify Client Secret\" class=\"input svelte-16m7f8c\"/></label> <label class=\"svelte-16m7f8c\"><span class=\"label-text svelte-16m7f8c\">Redirect URI (Auto-generated & Immutable)</span> <input type=\"text\" placeholder=\"Loading dynamic redirect URI...\" class=\"input readonly-input svelte-16m7f8c\"/></label> <button class=\"btn-primary svelte-16m7f8c\"> </button></div>"), ui = /* @__PURE__ */ Q("<button class=\"btn-secondary svelte-16m7f8c\">+ Add Account</button>"), di = /* @__PURE__ */ Q("<div class=\"add-account-form svelte-16m7f8c\"><input type=\"text\" placeholder=\"Account name\" class=\"input svelte-16m7f8c\"/> <button class=\"btn-primary svelte-16m7f8c\">Add</button> <button class=\"btn-secondary svelte-16m7f8c\">Cancel</button></div>"), fi = /* @__PURE__ */ Q("<span class=\"status-badge authenticated svelte-16m7f8c\">✓ Authenticated</span>"), pi = /* @__PURE__ */ Q("<span class=\"status-badge unauthenticated svelte-16m7f8c\">⚠ Not Authenticated</span>"), mi = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-16m7f8c\">● Active</span>"), hi = /* @__PURE__ */ Q("<div class=\"account-row svelte-16m7f8c\"><div class=\"account-info svelte-16m7f8c\"><div class=\"account-name svelte-16m7f8c\"> </div> <div class=\"account-status svelte-16m7f8c\"><!> <!></div></div> <div class=\"account-actions svelte-16m7f8c\"><button class=\"btn-link svelte-16m7f8c\"> </button> <button> </button> <button class=\"btn-delete svelte-16m7f8c\">✕</button></div></div>"), gi = /* @__PURE__ */ Q("<div class=\"empty-state svelte-16m7f8c\">No accounts added yet</div>"), _i = /* @__PURE__ */ Q("<div class=\"section svelte-16m7f8c\"><div class=\"section-header svelte-16m7f8c\"><h3 class=\"svelte-16m7f8c\">Global Credentials</h3> <button class=\"btn-secondary svelte-16m7f8c\"> </button></div> <!></div> <div class=\"section svelte-16m7f8c\"><div class=\"section-header svelte-16m7f8c\"><h3 class=\"svelte-16m7f8c\"> </h3> <!></div> <!> <div class=\"accounts-list svelte-16m7f8c\"></div></div>", 1), vi = /* @__PURE__ */ Q("<section class=\"spotify-card card svelte-16m7f8c\"><div class=\"card-header svelte-16m7f8c\"><div class=\"header-left svelte-16m7f8c\"><h2 class=\"svelte-16m7f8c\">Spotify</h2> <span class=\"provider-badge svelte-16m7f8c\">Streaming Service</span></div></div> <!></section>"), yi = {
	hash: "svelte-16m7f8c",
	code: ".spotify-card.svelte-16m7f8c {padding:20px;margin-bottom:16px;}.card-header.svelte-16m7f8c {display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid var(--border-color, rgba(255,255,255,0.1));}.header-left.svelte-16m7f8c {display:flex;align-items:center;gap:12px;}.card-header.svelte-16m7f8c h2:where(.svelte-16m7f8c) {margin:0;font-size:20px;font-weight:600;}.provider-badge.svelte-16m7f8c {font-size:12px;padding:4px 8px;border-radius:4px;background:rgba(29, 185, 84, 0.2);color:#1db954;}.section.svelte-16m7f8c {margin-bottom:24px;}.section.svelte-16m7f8c h3:where(.svelte-16m7f8c) {margin:0 0 12px 0;font-size:16px;font-weight:600;}.section-header.svelte-16m7f8c {display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;}.form-group.svelte-16m7f8c {display:flex;flex-direction:column;gap:12px;}label.svelte-16m7f8c {display:flex;flex-direction:column;gap:6px;}.label-text.svelte-16m7f8c {font-size:14px;color:var(--text);}.input.svelte-16m7f8c {padding:8px 12px;border-radius:6px;background:var(--input-bg, rgba(255,255,255,0.05));border:1px solid var(--border-color, rgba(255,255,255,0.1));color:var(--text);font-size:14px;}.input.svelte-16m7f8c:focus {outline:none;border-color:#1db954;}.readonly-input.svelte-16m7f8c {opacity:0.7;cursor:not-allowed;background:rgba(0, 0, 0, 0.2);user-select:all;}.btn-primary.svelte-16m7f8c, .btn-secondary.svelte-16m7f8c, .btn-link.svelte-16m7f8c, .btn-toggle.svelte-16m7f8c, .btn-delete.svelte-16m7f8c {padding:8px 16px;border-radius:6px;border:none;cursor:pointer;font-size:14px;transition:all 0.2s;}.btn-primary.svelte-16m7f8c {background:#1db954;color:white;}.btn-primary.svelte-16m7f8c:hover:not(:disabled) {background:#1ed760;}.btn-primary.svelte-16m7f8c:disabled {opacity:0.5;cursor:not-allowed;}.btn-secondary.svelte-16m7f8c {background:rgba(255,255,255,0.1);color:var(--text);}.btn-secondary.svelte-16m7f8c:hover {background:rgba(255,255,255,0.15);}.btn-link.svelte-16m7f8c {background:transparent;color:#1db954;padding:4px 8px;}.btn-link.svelte-16m7f8c:hover {text-decoration:underline;}.btn-toggle.svelte-16m7f8c {background:rgba(255,255,255,0.1);color:var(--text);}.btn-toggle.active.svelte-16m7f8c {background:rgba(29, 185, 84, 0.2);color:#1db954;}.btn-toggle.svelte-16m7f8c:hover {background:rgba(255,255,255,0.15);}.btn-delete.svelte-16m7f8c {background:rgba(239, 68, 68, 0.2);color:#ef4444;padding:6px 10px;}.btn-delete.svelte-16m7f8c:hover {background:rgba(239, 68, 68, 0.3);}.add-account-form.svelte-16m7f8c {display:flex;gap:8px;margin-bottom:12px;padding:12px;background:rgba(255,255,255,0.05);border-radius:6px;}.add-account-form.svelte-16m7f8c .input:where(.svelte-16m7f8c) {flex:1;}.accounts-list.svelte-16m7f8c {display:flex;flex-direction:column;gap:8px;}.account-row.svelte-16m7f8c {display:flex;justify-content:space-between;align-items:center;padding:12px;background:rgba(255,255,255,0.05);border-radius:6px;border:1px solid var(--border-color, rgba(255,255,255,0.1));}.account-info.svelte-16m7f8c {display:flex;flex-direction:column;gap:6px;}.account-name.svelte-16m7f8c {font-weight:500;font-size:14px;}.account-status.svelte-16m7f8c {display:flex;gap:8px;flex-wrap:wrap;}.status-badge.svelte-16m7f8c {font-size:12px;padding:2px 8px;border-radius:4px;}.status-badge.authenticated.svelte-16m7f8c {background:rgba(34, 197, 94, 0.2);color:#22c55e;}.status-badge.unauthenticated.svelte-16m7f8c {background:rgba(251, 191, 36, 0.2);color:#fbbf24;}.status-badge.active.svelte-16m7f8c {background:rgba(59, 130, 246, 0.2);color:#3b82f6;}.account-actions.svelte-16m7f8c {display:flex;gap:8px;align-items:center;}.empty-state.svelte-16m7f8c {padding:24px;text-align:center;color:var(--muted);}.loading.svelte-16m7f8c {padding:24px;text-align:center;color:var(--muted);}"
};
function bi(e, t) {
	He(t, !1), Rr(e, yi);
	let n = ti(t, "apiBase", 12, ""), r = /* @__PURE__ */ N(""), i = /* @__PURE__ */ N(""), a = /* @__PURE__ */ N(""), o = /* @__PURE__ */ N([]), s = /* @__PURE__ */ N(!1), c = /* @__PURE__ */ N(""), l = /* @__PURE__ */ N(!0), u = /* @__PURE__ */ N(!1), d = /* @__PURE__ */ N(!1);
	Tr(async () => {
		await f(), await m(), !X(a) && typeof window < "u" && P(a, `${window.location.protocol}//${window.location.host}/api/spotify/callback`), P(d, !!(X(r) && X(i) && X(a) && X(o).some((e) => e.is_authenticated))), P(l, !1);
	});
	async function f() {
		try {
			let e = await fetch(`${n()}/providers/spotify/settings`);
			e.data?.settings && (P(r, e.data.settings.client_id || ""), P(i, e.data.settings.client_secret || ""), P(a, e.data.settings.redirect_uri || ""));
		} catch (e) {
			console.error("Failed to load Spotify settings:", e);
		}
	}
	async function p() {
		if (!X(r) || !X(i)) {
			console.error("Client ID and Secret are required");
			return;
		}
		try {
			P(u, !0), await fetch(`${n()}/providers/spotify/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					client_id: X(r),
					client_secret: X(i),
					redirect_uri: X(a)
				})
			}), console.log("Spotify credentials saved");
		} catch (e) {
			throw console.error("Failed to save Spotify settings:", e), console.error("Failed to save credentials"), e;
		} finally {
			P(u, !1);
		}
	}
	async function m() {
		try {
			P(o, (await fetch(`${n()}/accounts/spotify`)).data?.accounts || []);
		} catch (e) {
			console.error("Failed to load Spotify accounts:", e), P(o, []);
		}
	}
	async function h() {
		if (!X(c).trim()) {
			console.error("Account name is required");
			return;
		}
		if (X(o).length >= 25) {
			console.error("Maximum 25 accounts allowed");
			return;
		}
		try {
			await fetch(`${n()}/accounts/spotify`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					account_name: X(c),
					display_name: X(c)
				})
			}), console.log("Account added"), P(c, ""), P(s, !1), await m();
		} catch (e) {
			console.error("Failed to add account:", e), console.error("Failed to add account");
		}
	}
	async function g(e, t) {
		try {
			await fetch(`${n()}/accounts/spotify/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			}), console.log(t ? "Account deactivated" : "Account activated"), await m();
		} catch (e) {
			console.error("Failed to toggle account:", e), console.error("Failed to update account");
		}
	}
	async function _(e, t) {
		if (confirm(`Delete account "${t}"?`)) try {
			await fetch(`${n()}/accounts/spotify/${e}`, { method: "DELETE" }), console.log("Account deleted"), await m();
		} catch (e) {
			console.error("Failed to delete account:", e), console.error("Failed to delete account");
		}
	}
	async function v(e) {
		if (!X(r) || !X(i)) {
			console.error("Please save Spotify Client ID and Client Secret before authenticating an account");
			return;
		}
		try {
			await p();
		} catch {
			return;
		}
		try {
			let t = (await fetch(`${n()}/spotify/auth`, { params: { account_id: e } })).data?.auth_url;
			t ? window.location.href = t : console.error("Failed to get Spotify auth URL");
		} catch (e) {
			console.error("Failed to start OAuth:", e);
			let t = e?.response?.data?.error || "Failed to start OAuth";
			console.error(t);
		}
	}
	var y = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), mt();
		}
	};
	$r();
	var b = vi(), x = R(L(b), 2), S = (e) => {
		$(e, ci());
	}, C = (e) => {
		var t = _i(), n = tn(t), l = L(n), f = R(L(l), 2), m = L(f, !0);
		O(f), O(l);
		var y = R(l, 2), b = (e) => {
			var t = li(), n = L(t), o = R(L(n), 2);
			Gr(o), O(n);
			var s = R(n, 2), c = R(L(s), 2);
			Gr(c), O(s);
			var l = R(s, 2), d = R(L(l), 2);
			Gr(d), d.readOnly = !0, d.disabled = !0, O(l);
			var f = R(l, 2), m = L(f, !0);
			O(f), O(t), Cn(() => {
				f.disabled = X(u), _r(m, X(u) ? "Saving..." : "Save Credentials");
			}), Xr(o, () => X(r), (e) => P(r, e)), Xr(c, () => X(i), (e) => P(i, e)), Xr(d, () => X(a), (e) => P(a, e)), cr("click", f, p), $(e, t);
		};
		Dr(y, (e) => {
			X(d) || e(b);
		}), O(n);
		var x = R(n, 2), S = L(x), C = L(S), w = L(C);
		O(C);
		var ee = R(C, 2), te = (e) => {
			var t = ui();
			cr("click", t, () => P(s, !X(s))), $(e, t);
		};
		Dr(ee, (e) => {
			X(o), Z(() => X(o).length < 25) && e(te);
		}), O(S);
		var ne = R(S, 2), re = (e) => {
			var t = di(), n = L(t);
			Gr(n);
			var r = R(n, 2), i = R(r, 2);
			O(t), Xr(n, () => X(c), (e) => P(c, e)), cr("keydown", n, (e) => e.key === "Enter" && h()), cr("click", r, h), cr("click", i, () => P(s, !1)), $(e, t);
		};
		Dr(ne, (e) => {
			X(s) && e(re);
		});
		var ie = R(ne, 2);
		Mr(ie, 5, () => X(o), Or, (e, t) => {
			var n = hi(), r = L(n), i = L(r), a = L(i, !0);
			O(i);
			var o = R(i, 2), s = L(o), c = (e) => {
				$(e, fi());
			}, l = (e) => {
				$(e, pi());
			};
			Dr(s, (e) => {
				X(t), Z(() => X(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = R(s, 2), d = (e) => {
				$(e, mi());
			};
			Dr(u, (e) => {
				X(t), Z(() => X(t).is_active) && e(d);
			}), O(o), O(r);
			var f = R(r, 2), p = L(f), m = L(p, !0);
			O(p);
			var h = R(p, 2);
			let y;
			var b = L(h, !0);
			O(h);
			var x = R(h, 2);
			O(f), O(n), Cn(() => {
				_r(a, (X(t), Z(() => X(t).display_name || X(t).account_name))), _r(m, (X(t), Z(() => X(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), y = Vr(h, 1, "btn-toggle svelte-16m7f8c", null, y, { active: X(t).is_active }), Kr(h, "title", (X(t), Z(() => X(t).is_active ? "Deactivate" : "Activate"))), _r(b, (X(t), Z(() => X(t).is_active ? "Deactivate" : "Activate")));
			}), cr("click", p, () => v(X(t).id)), cr("click", h, () => g(X(t).id, X(t).is_active)), cr("click", x, () => _(X(t).id, X(t).display_name || X(t).account_name)), $(e, n);
		}, (e) => {
			$(e, gi());
		}), O(ie), O(x), Cn(() => {
			_r(m, X(d) ? "Expand" : "Collapse"), _r(w, `Accounts (${(X(o), Z(() => X(o).length)) ?? ""}/25)`);
		}), cr("click", f, () => P(d, !X(d))), $(e, t);
	};
	return Dr(x, (e) => {
		X(l) ? e(S) : e(C, -1);
	}), O(b), $(e, b), Ue(y);
}
customElements.define("spotify-dashboard-card", si(bi, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { bi as default };

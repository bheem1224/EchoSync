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
	return D(/* @__PURE__ */ tn(E));
}
function O(e) {
	if (T) {
		if (/* @__PURE__ */ tn(E) !== null) throw je(), r;
		E = e;
	}
}
function Fe(e = 1) {
	if (T) {
		for (var t = e, n = E; t--;) n = /* @__PURE__ */ tn(n);
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
		var i = /* @__PURE__ */ tn(n);
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
		r: W,
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
		for (var r of n) _n(r);
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
	var t = W;
	if (t === null) return V.f |= de, e;
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
				o ? i.f ^= S : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : Jn(i) && (a & 16 && this.#l.add(i), $n(i));
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
			if (lt !== null && n === W && (e || (V === null || !(V.f & 2)) && !tt)) return;
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
			if (!(r.f & 24576) && Jn(r) && (gt = /* @__PURE__ */ new Set(), $n(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && An(r), gt?.size > 0)) {
				Bt.clear();
				for (let e of gt) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) gt.has(n) && (gt.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || $n(n);
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
		mn() && (Y(n), Cn(() => (t === 0 && (r = X(() => e(() => Kt(n)))), t += 1, () => {
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
			var t = W;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = W.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Tn(() => {
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
			this.#a = z(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = z(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = z(() => e(this.#e)), qe(() => {
			var e = this.#c = document.createDocumentFragment(), t = F();
			e.append(t), this.#a = this.#x(() => z(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, jn(this.#o, () => {
				this.#o = null;
			}), this.#b(j));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = z(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Fn(this.#a, e);
				let t = this.#n.pending;
				this.#o = z(() => t(this.#e));
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
		var t = W, n = V, r = k;
		Bn(this.#i), U(this.#i), Ve(this.#i.ctx);
		try {
			return pt.ensure(), e();
		} catch (e) {
			return Ye(e), null;
		} finally {
			Bn(t), U(n), Ve(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && jn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, qe(() => {
			this.#d = !1, this.#m && Wt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Y(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		j?.is_fork ? (this.#a && j.skip_effect(this.#a), this.#o && j.skip_effect(this.#o), this.#s && j.skip_effect(this.#s), j.on_fork_commit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (B(this.#a), null), this.#o &&= (B(this.#o), null), this.#s &&= (B(this.#s), null), T && (D(this.#t), Fe(), D(Ie()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Me();
				return;
			}
			r = !0, i && ke(), this.#s !== null && jn(this.#s, () => {
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
					return z(() => {
						var t = W;
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
	var o = W, s = Ot(), c = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
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
	var e = W, t = V, n = k, r = j;
	return function(i = !0) {
		Bn(e), U(t), Ve(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function kt(e = !0) {
	Bn(null), U(null), Ve(null), e && j?.deactivate();
}
function At() {
	var e = W, t = e.b, n = j, r = t.is_rendered();
	return t.update_pending_count(1, n), n.increment(r, e), (i = !1) => {
		t.update_pending_count(-1, n), n.decrement(r, e, i);
	};
}
/* @__NO_SIDE_EFFECTS__ */
function jt(e) {
	var t = 2 | C;
	return W !== null && (W.f |= ae), {
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
		parent: W,
		ac: null
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Mt(e, t, n) {
	let r = W;
	r === null && ve();
	var a = void 0, o = Ht(i), s = !V, c = /* @__PURE__ */ new Map();
	return Sn(() => {
		var t = W, n = x();
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
	}), hn(() => {
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
		for (var n = 0; n < t.length; n += 1) B(t[n]);
	}
}
function Ft(e) {
	var t, n = W, r = e.parent;
	if (!Rn && r !== null && r.f & 24576) return Ae(), e.v;
	Bn(r);
	try {
		e.f &= ~ce, Pt(e), t = Xn(e);
	} finally {
		Bn(n);
	}
	return t;
}
function It(e) {
	var t = Ft(e);
	if (!e.equals(t) && (e.wv = qn(), (!j?.is_fork || e.deps === null) && (j === null ? e.v = t : j.capture(e, t, !0), e.deps === null))) {
		A(e, S);
		return;
	}
	Rn || (M === null ? Qe(e) : (mn() || j?.is_fork) && M.set(e, t));
}
function Lt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(he), t.teardown = v, t.ac = null, Qn(t, 0), Dn(t));
}
function Rt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && $n(t);
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
	return Vn(n), n;
}
/* @__NO_SIDE_EFFECTS__ */
function N(e, n = !1, r = !0) {
	let i = Ht(e);
	return n || (i.equals = Be), t && r && k !== null && k.l !== null && (k.l.s ??= []).push(i), i;
}
function P(e, t, n = !1) {
	return V !== null && (!H || V.f & 131072) && We() && V.f & 4325394 && (G === null || !c.call(G, e)) && Oe(), Wt(e, n ? Jt(t) : t, ut);
}
function Wt(e, t, n = null) {
	if (!e.equals(t)) {
		Bt.set(e, Rn ? t : e.v);
		var r = pt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Ft(t), M === null && Qe(t);
		}
		e.wv = qn(), qt(e, C, n), We() && W !== null && W.f & 1024 && !(W.f & 96) && (J === null ? Hn([e]) : J.push(e)), !r.is_fork && zt.size > 0 && !Vt && Gt();
	}
	return t;
}
function Gt() {
	Vt = !1;
	for (let e of zt) e.f & 1024 && A(e, w), Jn(e) && $n(e);
	zt.clear();
}
function Kt(e) {
	P(e, e.v + 1);
}
function qt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = We(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === W)) {
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
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ Ut(0), s = null, c = Gn, l = (e) => {
		if (Gn === c) return e();
		var t = V, n = Gn;
		U(null), Kn(c);
		var r = e();
		return U(t), Kn(n), r;
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
				var u = Y(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = Y(a));
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
			return (r !== void 0 || W !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ Ut(a ? Jt(e[t]) : i, s)), n.set(t, r)), Y(r) === i) ? !1 : a;
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
			Y(a);
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
function tn(e) {
	return Qt.call(e);
}
function I(e, t) {
	if (!T) return /* @__PURE__ */ en(e);
	var n = /* @__PURE__ */ en(E);
	if (n === null) n = E.appendChild(F());
	else if (t && n.nodeType !== 3) {
		var r = F();
		return n?.before(r), D(r), r;
	}
	return t && sn(n), D(n), n;
}
function nn(e, t = !1) {
	if (!T) {
		var n = /* @__PURE__ */ en(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ tn(n) : n;
	}
	if (t) {
		if (E?.nodeType !== 3) {
			var r = F();
			return E?.before(r), D(r), r;
		}
		sn(E);
	}
	return E;
}
function L(e, t = 1, n = !1) {
	let r = T ? E : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ tn(r);
	if (!T) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = F();
			return r === null ? i?.after(a) : r.before(a), D(a), a;
		}
		sn(r);
	}
	return D(r), r;
}
function rn(e) {
	e.textContent = "";
}
function an() {
	return !e || gt !== null ? !1 : (W.f & ne) !== 0;
}
function on(e, t, n) {
	let r = n ? { is: n } : void 0;
	return document.createElementNS(t ?? "http://www.w3.org/1999/xhtml", e, r);
}
function sn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var cn = !1;
function ln() {
	cn || (cn = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t.__on_r?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function un(e) {
	var t = V, n = W;
	U(null), Bn(null);
	try {
		return e();
	} finally {
		U(t), Bn(n);
	}
}
function dn(e, t, n, r = n) {
	e.addEventListener(t, () => un(n));
	let i = e.__on_r;
	i ? e.__on_r = () => {
		i(), r(!0);
	} : e.__on_r = () => r(!0), ln();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function fn(e) {
	W === null && (V === null && Se(e), xe()), Rn && be(e);
}
function pn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function R(e, t) {
	var n = W;
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
			$n(r);
		} catch (e) {
			throw B(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= ie));
	}
	if (i !== null && (i.parent = n, n !== null && pn(i, n), V !== null && V.f & 2 && !(e & 64))) {
		var a = V;
		(a.effects ??= []).push(i);
	}
	return r;
}
function mn() {
	return V !== null && !H;
}
function hn(e) {
	let t = R(8, null);
	return A(t, S), t.teardown = e, t;
}
function gn(e) {
	fn("$effect");
	var t = W.f;
	if (!V && t & 32 && !(t & 32768)) {
		var n = k;
		(n.e ??= []).push(e);
	} else return _n(e);
}
function _n(e) {
	return R(4 | oe, e);
}
function vn(e) {
	return fn("$effect.pre"), R(8 | oe, e);
}
function yn(e) {
	pt.ensure();
	let t = R(64 | ae, e);
	return () => {
		B(t);
	};
}
function bn(e) {
	pt.ensure();
	let t = R(64 | ae, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? jn(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function xn(e) {
	return R(4, e);
}
function Sn(e) {
	return R(ue | ae, e);
}
function Cn(e, t = 0) {
	return R(8 | t, e);
}
function wn(e, t = [], n = [], r = []) {
	Dt(r, t, n, (t) => {
		R(8, () => e(...t.map(Y)));
	});
}
function Tn(e, t = 0) {
	return R(16 | t, e);
}
function z(e) {
	return R(32 | ae, e);
}
function En(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = Rn, n = V;
		zn(!0), U(null);
		try {
			t.call(null);
		} finally {
			zn(e), U(n);
		}
	}
}
function Dn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && un(() => {
			e.abort(he);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function On(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (kn(e.nodes.start, e.nodes.end), n = !0), A(e, re), Dn(e, t && !n), Qn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	En(e), e.f ^= re, e.f |= te;
	var i = e.parent;
	i !== null && i.first !== null && An(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function kn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ tn(e);
		e.remove(), e = n;
	}
}
function An(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function jn(e, t, n = !0) {
	var r = [];
	Mn(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function Mn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ee;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				Mn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Nn(e) {
	Pn(e, !0);
}
function Pn(e, t) {
	if (e.f & 8192) {
		e.f ^= ee, e.f & 1024 || (A(e, C), pt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Pn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Fn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ tn(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var In = null, Ln = !1, Rn = !1;
function zn(e) {
	Rn = e;
}
var V = null, H = !1;
function U(e) {
	V = e;
}
var W = null;
function Bn(e) {
	W = e;
}
var G = null;
function Vn(t) {
	V !== null && (!e || V.f & 2) && (G === null ? G = [t] : G.push(t));
}
var K = null, q = 0, J = null;
function Hn(e) {
	J = e;
}
var Un = 1, Wn = 0, Gn = Wn;
function Kn(e) {
	Gn = e;
}
function qn() {
	return ++Un;
}
function Jn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~ce), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Jn(a) && It(a), a.wv > e.wv) return !0;
		}
		t & 512 && M === null && A(e, S);
	}
	return !1;
}
function Yn(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && G !== null && c.call(G, t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? Yn(o, n, !1) : n === o && (r ? A(o, C) : o.f & 1024 && A(o, w), bt(o));
	}
}
function Xn(e) {
	var t = K, n = q, r = J, i = V, a = G, o = k, s = H, c = Gn, l = e.f;
	K = null, q = 0, J = null, V = l & 96 ? null : e, G = null, Ve(e.ctx), H = !1, Gn = ++Wn, e.ac !== null && (un(() => {
		e.ac.abort(he);
	}), e.ac = null);
	try {
		e.f |= le;
		var u = e.fn, d = u();
		e.f |= ne;
		var f = e.deps, p = j?.is_fork;
		if (K !== null) {
			var m;
			if (p || Qn(e, q), f !== null && q > 0) for (f.length = q + K.length, m = 0; m < K.length; m++) f[q + m] = K[m];
			else e.deps = f = K;
			if (mn() && e.f & 512) for (m = q; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && q < f.length && (Qn(e, q), f.length = q);
		if (We() && J !== null && !H && f !== null && !(e.f & 6146)) for (m = 0; m < J.length; m++) Yn(J[m], e);
		if (i !== null && i !== e) {
			if (Wn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Wn;
			if (t !== null) for (let e of t) e.rv = Wn;
			J !== null && (r === null ? r = J : r.push(...J));
		}
		return e.f & 8388608 && (e.f ^= de), d;
	} catch (e) {
		return Ye(e);
	} finally {
		e.f ^= le, K = t, q = n, J = r, V = i, G = a, Ve(o), H = s, Gn = c;
	}
}
function Zn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (K === null || !c.call(K, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~ce), o.v !== i && Qe(o), Lt(o), Qn(o, 0);
	}
}
function Qn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Zn(e, n[r]);
}
function $n(e) {
	var t = e.f;
	if (!(t & 16384)) {
		A(e, S);
		var n = W, r = Ln;
		W = e, Ln = !0;
		try {
			t & 16777232 ? On(e) : Dn(e), En(e);
			var i = Xn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Un;
		} finally {
			Ln = r, W = n;
		}
	}
}
async function er() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), mt();
}
function Y(e) {
	var t = (e.f & 2) != 0;
	if (In?.add(e), V !== null && !H && !(W !== null && W.f & 16384) && (G === null || !c.call(G, e))) {
		var n = V.deps;
		if (V.f & 2097152) e.rv < Wn && (e.rv = Wn, K === null && n !== null && n[q] === e ? q++ : K === null ? K = [e] : K.push(e));
		else {
			(V.deps ??= []).push(e);
			var r = e.reactions;
			r === null ? e.reactions = [V] : c.call(r, V) || r.push(V);
		}
	}
	if (Rn && Bt.has(e)) return Bt.get(e);
	if (t) {
		var i = e;
		if (Rn) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || nr(i)) && (a = Ft(i)), Bt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !H && V !== null && (Ln || (V.f & 512) != 0), s = (i.f & ne) === 0;
		Jn(i) && (o && (i.f |= 512), It(i)), o && !s && (Rt(i), tr(i));
	}
	if (M?.has(e)) return M.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function tr(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Rt(t), tr(t));
}
function nr(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Bt.has(t) || t.f & 2 && nr(t)) return !0;
	return !1;
}
function X(e) {
	var t = H;
	try {
		return H = !0, e();
	} finally {
		H = t;
	}
}
function rr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (fe in e) ir(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && fe in n && ir(n);
		}
	}
}
function ir(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			ir(e[n], t);
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
var ar = Symbol("events"), or = /* @__PURE__ */ new Set(), sr = /* @__PURE__ */ new Set();
function cr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || ur.call(t, e), !e.cancelBubble) return un(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? qe(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function Z(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = cr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && hn(() => {
		t.removeEventListener(e, o, a);
	});
}
var lr = null;
function ur(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	lr = e;
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
		d(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var u = V, f = W;
		U(null), Bn(null);
		try {
			for (var p, m = []; a !== null;) {
				var h = a.assignedSlot || a.parentNode || a.host || null;
				try {
					var g = a[ar]?.[r];
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
			e[ar] = t, delete e.currentTarget, U(u), Bn(f);
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
	var t = on("template");
	return t.innerHTML = fr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function mr(e, t) {
	var n = W;
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
		var n = W;
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
		for (var o = /* @__PURE__ */ en(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ tn(o);
		if (!o) throw r;
		Ne(!0), D(o);
		let i = xr(e, {
			...t,
			anchor: o
		});
		return Ne(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && we(), $t(), rn(n), Ne(!1), vr(e, t);
	} finally {
		Ne(i), D(a);
	}
}
var br = /* @__PURE__ */ new Map();
function xr(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	$t();
	var u = void 0, d = bn(() => {
		var s = n ?? t.appendChild(F());
		Tt(s, { pending: () => {} }, (t) => {
			He({});
			var n = k;
			if (o && (n.c = o), a && (i.$$events = a), T && mr(t, null), u = e(t, i) || {}, T && (W.nodes.end = E, E === null || E.nodeType !== 8 || E.data !== "]")) throw je(), r;
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
		return f(l(or)), sr.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = br.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, ur), r.delete(e), r.size === 0 && br.delete(n)) : r.set(e, i);
			}
			sr.delete(f), s !== n && s.parentNode?.removeChild(s);
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
			if (n) Nn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
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
						Fn(r, t), t.append(F()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), jn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = j, r = an();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = F();
			i.append(a), this.#n.set(e, {
				effect: z(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, z(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else T && (this.anchor = E), this.#a(n);
	}
};
function Tr(e) {
	k === null && _e("onMount"), t && k.l !== null ? Er(k).m.push(e) : gn(() => {
		let t = X(e);
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
	Tn(() => {
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
		jn(n, () => {
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
			rn(d), d.append(u), e.items.clear();
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
		r?.has(a) ? (a.f |= se, Fn(a, document.createDocumentFragment())) : B(t[i], n);
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
		v.effect.f & 16384 || (v.pending.delete(e), v.fallback = d, Pr(v, p, s, t, r), d !== null && (p.length === 0 ? d.f & 33554432 ? (d.f ^= se, Ir(d, null, s)) : Nn(d) : jn(d, () => {
			d = null;
		})));
	}
	function _(e) {
		v.pending.delete(e);
	}
	var v = {
		effect: Tn(() => {
			p = Y(f);
			var e = p.length;
			let o = !1;
			T && Le(s) === "[!" != (e === 0) && (s = Ie(), D(s), Ne(!1), o = !0);
			for (var l = /* @__PURE__ */ new Set(), u = j, v = an(), y = 0; y < e; y += 1) {
				T && E.nodeType === 8 && E.data === "]" && (s = E, o = !0, Ne(!1));
				var b = p[y], x = r(b, y), S = h ? null : c.get(x);
				S ? (S.v && Wt(S.v, b), S.i && Wt(S.i, y), v && u.unskip_effect(S.e)) : (S = Fr(c, h ? s : jr ??= F(), b, x, y, i, t, n), h || (S.e.f |= se), c.set(x, S)), l.add(x);
			}
			if (e === 0 && a && !d && (h ? d = z(() => a(s)) : (d = z(() => a(jr ??= F())), d.f |= se)), e > l.size && ye("", "", ""), T && e > 0 && D(Ie()), !h) if (m.set(u, l), v) {
				for (let [e, t] of c) l.has(e) || u.skip_effect(t.e);
				u.oncommit(g), u.ondiscard(_);
			} else g(u);
			o && Ne(!0), Y(f);
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
		if (_.f & 8192 && (Nn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) if (_.f ^= se, _ === c) Ir(_, null, n);
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
		e: z(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function Ir(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ tn(r);
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
	xn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = on("style");
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
var Hr = Symbol("is custom element"), Ur = Symbol("is html"), Wr = ge ? "link" : "LINK", Gr = ge ? "progress" : "PROGRESS";
function Kr(e) {
	if (T) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Jr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Jr(e, "checked", null), e.checked = r;
				}
			}
		};
		e.__on_r = n, qe(n), ln();
	}
}
function qr(e, t) {
	var n = Yr(e);
	n.value === (n.value = t ?? void 0) || e.value === t && (t !== 0 || e.nodeName !== Gr) || (e.value = t ?? "");
}
function Jr(e, t, n, r) {
	var i = Yr(e);
	T && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Wr) || i[t] !== (i[t] = n) && (t === "loading" && (e[me] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Zr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function Yr(e) {
	return e.__attributes ??= {
		[Hr]: e.nodeName.includes("-"),
		[Ur]: e.namespaceURI === a
	};
}
var Xr = /* @__PURE__ */ new Map();
function Zr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Xr.get(t);
	if (n) return n;
	Xr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Qr(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	dn(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = $r(t) ? ei(a) : a, r(a), j !== null && i.add(j), await er(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (T && t.defaultValue !== t.value || X(n) == null && t.value) && (r($r(t) ? ei(t.value) : t.value), j !== null && i.add(j)), Cn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? at : j;
			if (i.has(a)) return;
		}
		$r(t) && r === ei(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function $r(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function ei(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function ti(e) {
	return function(...t) {
		return t[0].stopPropagation(), e?.apply(this, t);
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function ni(e = !1) {
	let t = k, n = t.l.u;
	if (!n) return;
	let r = () => rr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ jt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Y(i);
	}
	n.b.length && vn(() => {
		ri(t, r), b(n.b);
	}), gn(() => {
		let e = X(() => n.m.map(y));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && gn(() => {
		ri(t, r), b(n.a);
	});
}
function ri(e, t) {
	if (e.l.s) for (let t of e.l.s) Y(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/misc.js
function ii(e, t) {
	var n = e.$$events?.[t.type];
	for (var r of o(n) ? n.slice() : n == null ? [] : [n]) r.call(this, t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function ai(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = () => (l && (l = !1, c = s ? X(i) : i), c);
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
	o && Y(y);
	var b = W;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Y(y) : a && o ? Jt(e) : e;
			return P(y, n), v = !0, c !== void 0 && (c = n), e;
		}
		return Rn && v || b.f & 16384 ? y.v : Y(y);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function oi(e) {
	return new si(e);
}
var si = class {
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
				return Y(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === pe ? !0 : (Y(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
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
}, ci;
typeof HTMLElement == "function" && (ci = class extends HTMLElement {
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
			let t = {}, n = ui(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = li(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = oi({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = yn(() => {
				Cn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = li(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = li(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
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
function li(e, t, n, r) {
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
function ui(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function di(e, t, n, r, i, a) {
	let o = class extends ci {
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
				n = li(e, n, t), this.$$d[e] = n;
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
//#region MusicBrainzCard.svelte
var fi = /* @__PURE__ */ Q("<div class=\"loading svelte-1ghyjz5\">Loading...</div>"), pi = /* @__PURE__ */ Q("<input type=\"text\" class=\"input readonly-input svelte-1ghyjz5\" readonly=\"\" disabled=\"\"/> <p class=\"help-text svelte-1ghyjz5\" style=\"margin-top:6px;\">Add this URI as a callback URL in your MusicBrainz application settings.</p>", 1), mi = /* @__PURE__ */ Q("<button class=\"btn-secondary svelte-1ghyjz5\">+ Add Account</button>"), hi = /* @__PURE__ */ Q("<span class=\"status-badge authenticated svelte-1ghyjz5\">✓ Authenticated</span>"), gi = /* @__PURE__ */ Q("<span class=\"status-badge unauthenticated svelte-1ghyjz5\">⚠ Not Authenticated</span>"), _i = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-1ghyjz5\">● Active</span>"), vi = /* @__PURE__ */ Q("<div class=\"account-row svelte-1ghyjz5\"><div class=\"account-info svelte-1ghyjz5\"><div class=\"account-name svelte-1ghyjz5\"> </div> <div class=\"account-status svelte-1ghyjz5\"><!> <!></div></div> <div class=\"account-actions svelte-1ghyjz5\"><button class=\"btn-link svelte-1ghyjz5\"> </button> <button> </button> <button class=\"btn-delete svelte-1ghyjz5\">✕</button></div></div>"), yi = /* @__PURE__ */ Q("<div class=\"empty-state svelte-1ghyjz5\">No accounts added yet. Click \"Add Account\" to get started.</div>"), bi = /* @__PURE__ */ Q("<div class=\"section svelte-1ghyjz5\"><h3 class=\"svelte-1ghyjz5\">Application Credentials</h3> <p class=\"help-text svelte-1ghyjz5\">Register an application at <a href=\"https://musicbrainz.org/account/applications\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"svelte-1ghyjz5\">musicbrainz.org/account/applications</a> to obtain a Client ID and Secret. These are required for OAuth logins and ISRC submissions.</p> <div class=\"creds-form svelte-1ghyjz5\"><div class=\"form-row svelte-1ghyjz5\"><label class=\"form-label svelte-1ghyjz5\" for=\"mb-client-id\">Client ID</label> <input id=\"mb-client-id\" type=\"text\" class=\"input svelte-1ghyjz5\" placeholder=\"Enter your MusicBrainz Client ID\"/></div> <div class=\"form-row svelte-1ghyjz5\"><label class=\"form-label svelte-1ghyjz5\" for=\"mb-client-secret\">Client Secret</label> <div class=\"password-field svelte-1ghyjz5\"><input id=\"mb-client-secret\" class=\"input svelte-1ghyjz5\"/> <button type=\"button\" class=\"password-toggle svelte-1ghyjz5\"> </button></div></div> <button class=\"btn-primary svelte-1ghyjz5\"> </button></div></div> <div class=\"section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"svelte-1ghyjz5\">OAuth Redirect URI (Auto-generated)</h3> <button class=\"btn-secondary svelte-1ghyjz5\"> </button></div> <!></div> <div class=\"section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"svelte-1ghyjz5\"> </h3> <p class=\"help-text svelte-1ghyjz5\">Each account represents a MusicBrainz user that will authenticate via OAuth.\n          Authenticated accounts can contribute ISRCs and metadata to MusicBrainz.</p> <!></div> <div class=\"accounts-list svelte-1ghyjz5\"></div></div>", 1), xi = /* @__PURE__ */ Q("<div class=\"modal-overlay svelte-1ghyjz5\"><div class=\"modal-content svelte-1ghyjz5\"><div class=\"modal-header svelte-1ghyjz5\"><h3 class=\"svelte-1ghyjz5\">Add MusicBrainz Account</h3> <button class=\"modal-close svelte-1ghyjz5\">✕</button></div> <div class=\"modal-body svelte-1ghyjz5\"><label><span class=\"label-text svelte-1ghyjz5\">Display Name</span> <input type=\"text\" placeholder=\"e.g. My MusicBrainz Username\" class=\"input svelte-1ghyjz5\"/></label> <p class=\"modal-help svelte-1ghyjz5\">Give this slot a friendly name. After adding, click \"Authenticate\" to link it\n          to a real MusicBrainz account via OAuth.</p></div> <div class=\"modal-footer svelte-1ghyjz5\"><button class=\"btn-secondary svelte-1ghyjz5\">Cancel</button> <button class=\"btn-primary svelte-1ghyjz5\"> </button></div></div></div>"), Si = /* @__PURE__ */ Q("<section class=\"mb-card card svelte-1ghyjz5\"><div class=\"card-header svelte-1ghyjz5\"><div class=\"header-left svelte-1ghyjz5\"><h2 class=\"svelte-1ghyjz5\">MusicBrainz</h2> <span class=\"provider-badge svelte-1ghyjz5\">Metadata</span></div></div> <!></section> <!>", 1), Ci = {
	hash: "svelte-1ghyjz5",
	code: ".mb-card.svelte-1ghyjz5 {padding:20px;margin-bottom:16px;}.card-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid var(--border-color, rgba(255,255,255,0.1));}.header-left.svelte-1ghyjz5 {display:flex;align-items:center;gap:12px;}.card-header.svelte-1ghyjz5 h2:where(.svelte-1ghyjz5) {margin:0;font-size:20px;font-weight:600;}.provider-badge.svelte-1ghyjz5 {font-size:12px;padding:4px 8px;border-radius:4px;background:rgba(186, 100, 21, 0.2);color:#ba6415;}.section.svelte-1ghyjz5 {margin-bottom:24px;}.section.svelte-1ghyjz5 h3:where(.svelte-1ghyjz5) {margin:0 0 8px 0;font-size:16px;font-weight:600;}.section-header.svelte-1ghyjz5 {margin-bottom:12px;}.section-header.svelte-1ghyjz5 h3:where(.svelte-1ghyjz5) {margin-bottom:4px;}.section-header.svelte-1ghyjz5 button:where(.svelte-1ghyjz5) {margin-top:8px;}.help-text.svelte-1ghyjz5 {font-size:13px;color:var(--muted);margin:0 0 12px 0;}.help-text.svelte-1ghyjz5 a:where(.svelte-1ghyjz5) {color:#ba6415;text-decoration:underline;}.creds-form.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:12px;}.form-row.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:4px;}.form-label.svelte-1ghyjz5 {font-size:13px;font-weight:500;color:var(--text);}.password-field.svelte-1ghyjz5 {display:flex;gap:6px;}.password-field.svelte-1ghyjz5 .input:where(.svelte-1ghyjz5) {flex:1;}.password-toggle.svelte-1ghyjz5 {background:rgba(255,255,255,0.08);border:1px solid var(--border-color, rgba(255,255,255,0.1));border-radius:6px;padding:0 10px;cursor:pointer;font-size:16px;color:var(--text);}.input.svelte-1ghyjz5 {padding:8px 12px;border-radius:6px;background:var(--input-bg, rgba(255,255,255,0.05));border:1px solid var(--border-color, rgba(255,255,255,0.1));color:var(--text);font-size:14px;width:100%;box-sizing:border-box;}.input.svelte-1ghyjz5:focus {outline:none;border-color:#ba6415;}.readonly-input.svelte-1ghyjz5 {opacity:0.7;cursor:not-allowed;background:rgba(0,0,0,0.2);user-select:all;}.btn-primary.svelte-1ghyjz5,\n  .btn-secondary.svelte-1ghyjz5,\n  .btn-link.svelte-1ghyjz5,\n  .btn-toggle.svelte-1ghyjz5,\n  .btn-delete.svelte-1ghyjz5 {padding:8px 16px;border-radius:6px;border:none;cursor:pointer;font-size:14px;transition:all 0.2s;}.btn-primary.svelte-1ghyjz5 {background:#ba6415;color:white;}.btn-primary.svelte-1ghyjz5:hover:not(:disabled) {background:#9d5412;}.btn-primary.svelte-1ghyjz5:disabled {opacity:0.5;cursor:not-allowed;}.btn-secondary.svelte-1ghyjz5 {background:rgba(255,255,255,0.1);color:var(--text);}.btn-secondary.svelte-1ghyjz5:hover {background:rgba(255,255,255,0.15);}.btn-link.svelte-1ghyjz5 {background:transparent;color:#ba6415;padding:4px 8px;}.btn-link.svelte-1ghyjz5:hover {text-decoration:underline;}.btn-toggle.svelte-1ghyjz5 {background:rgba(255,255,255,0.1);color:var(--text);}.btn-toggle.active.svelte-1ghyjz5 {background:rgba(186,100,21,0.2);color:#ba6415;}.btn-toggle.svelte-1ghyjz5:hover {background:rgba(255,255,255,0.15);}.btn-delete.svelte-1ghyjz5 {background:rgba(239,68,68,0.2);color:#ef4444;}.btn-delete.svelte-1ghyjz5:hover {background:rgba(239,68,68,0.3);}.accounts-list.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:8px;}.account-row.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;padding:12px;background:var(--input-bg, rgba(255,255,255,0.03));border:1px solid var(--border-color, rgba(255,255,255,0.08));border-radius:8px;}.account-info.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:4px;}.account-name.svelte-1ghyjz5 {font-weight:500;font-size:14px;}.account-status.svelte-1ghyjz5 {display:flex;gap:6px;flex-wrap:wrap;}.account-actions.svelte-1ghyjz5 {display:flex;gap:8px;align-items:center;flex-wrap:wrap;}.status-badge.svelte-1ghyjz5 {font-size:11px;padding:2px 6px;border-radius:4px;}.status-badge.authenticated.svelte-1ghyjz5 {background:rgba(34,197,94,0.2);color:#22c55e;}.status-badge.unauthenticated.svelte-1ghyjz5 {background:rgba(234,179,8,0.2);color:#eab308;}.status-badge.active.svelte-1ghyjz5 {background:rgba(186,100,21,0.2);color:#ba6415;}.empty-state.svelte-1ghyjz5 {padding:16px;text-align:center;color:var(--muted);font-size:14px;}.loading.svelte-1ghyjz5 {padding:24px;text-align:center;color:var(--muted);}\n\n  /* Modal */.modal-overlay.svelte-1ghyjz5 {position:fixed;inset:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:1000;}.modal-content.svelte-1ghyjz5 {background:var(--bg-elevated, #1e1e2e);border-radius:10px;padding:0;min-width:420px;max-width:90vw;border:1px solid var(--border-color, rgba(255,255,255,0.15));}.modal-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid var(--border-color, rgba(255,255,255,0.1));}.modal-header.svelte-1ghyjz5 h3:where(.svelte-1ghyjz5) {margin:0;font-size:16px;font-weight:600;}.modal-close.svelte-1ghyjz5 {background:transparent;border:none;font-size:18px;cursor:pointer;color:var(--muted);padding:0;line-height:1;}.modal-body.svelte-1ghyjz5 {padding:20px;display:flex;flex-direction:column;gap:14px;}.label-text.svelte-1ghyjz5 {display:block;font-size:13px;font-weight:500;margin-bottom:4px;color:var(--text);}.modal-help.svelte-1ghyjz5 {font-size:12px;color:var(--muted);margin:0;}.modal-footer.svelte-1ghyjz5 {display:flex;justify-content:flex-end;gap:10px;padding:16px 20px;border-top:1px solid var(--border-color, rgba(255,255,255,0.1));}"
};
function wi(e, t) {
	He(t, !1), Rr(e, Ci);
	let n = ai(t, "apiBase", 12, ""), r = /* @__PURE__ */ N(!0), i = /* @__PURE__ */ N([]), a = /* @__PURE__ */ N(""), o = /* @__PURE__ */ N(""), s = /* @__PURE__ */ N(""), c = !1, l = /* @__PURE__ */ N(!1), u = /* @__PURE__ */ N(!1), d = /* @__PURE__ */ N(!1), f = /* @__PURE__ */ N(!1), p = /* @__PURE__ */ N(!1), m = /* @__PURE__ */ N(""), h = /* @__PURE__ */ N(!1);
	Tr(async () => {
		await g(), P(r, !1);
	});
	async function g() {
		try {
			let e = await fetch(`${n()}/musicbrainz/accounts`);
			e.data && (P(i, e.data.accounts || []), P(a, e.data.redirect_uri || ""), c = e.data.client_id_configured || !1, P(l, e.data.client_secret_configured || !1), P(f, !!Y(a)));
			let t = await fetch(`${n()}/providers/musicbrainz/credentials`);
			t.data?.credentials && (P(o, t.data.credentials.client_id || ""), Y(l));
		} catch (e) {
			console.error("Failed to load MusicBrainz data:", e), console.error("Failed to load MusicBrainz settings");
		}
	}
	async function _() {
		if (!Y(o).trim()) {
			console.error("Client ID is required");
			return;
		}
		let e = { client_id: Y(o) };
		if (Y(s).trim()) e.client_secret = Y(s);
		else if (!Y(l)) {
			console.error("Client Secret is required");
			return;
		}
		try {
			P(d, !0), await fetch(`${n()}/providers/musicbrainz/credentials`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ credentials: e })
			}), console.log("MusicBrainz credentials saved"), P(s, ""), await g();
		} catch (e) {
			console.error("Failed to save credentials"), console.error(e);
		} finally {
			P(d, !1);
		}
	}
	function v() {
		P(m, ""), P(p, !0);
	}
	function y() {
		P(p, !1), P(m, "");
	}
	async function b() {
		let e = Y(m).trim();
		if (!e) {
			console.error("Account name is required");
			return;
		}
		try {
			P(h, !0), await fetch(`${n()}/musicbrainz/accounts`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ account_name: e })
			}), console.log("Account added"), y(), await g();
		} catch (e) {
			console.error("Failed to add account"), console.error(e);
		} finally {
			P(h, !1);
		}
	}
	async function x(e, t) {
		if (confirm(`Delete account "${t}"? This will also remove its stored tokens.`)) try {
			await fetch(`${n()}/musicbrainz/accounts/${e}`, { method: "DELETE" }), console.log("Account deleted"), await g();
		} catch {
			console.error("Failed to delete account");
		}
	}
	async function S(e, t) {
		try {
			await fetch(`${n()}/musicbrainz/accounts/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			}), console.log(t ? "Account deactivated" : "Account activated"), await g();
		} catch {
			console.error("Failed to update account status");
		}
	}
	async function C(e) {
		if (!c || !Y(l)) {
			console.log("Save your MusicBrainz Client ID and Client Secret before authenticating.", "error");
			return;
		}
		try {
			let t = (await fetch(`${n()}/musicbrainz/auth`, { params: { account_id: e } })).data?.auth_url;
			t ? (window.open(t, "_blank", "noopener,noreferrer"), setTimeout(async () => {
				await g();
			}, 5e3)) : console.error("Failed to get MusicBrainz auth URL");
		} catch (e) {
			let t = e?.response?.data?.error || "Failed to start OAuth";
			console.error(t);
		}
	}
	var w = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), mt();
		}
	};
	ni();
	var ee = Si(), te = nn(ee), ne = L(I(te), 2), re = (e) => {
		$(e, fi());
	}, ie = (e) => {
		var t = bi(), n = nn(t), r = L(I(n), 4), c = I(r), p = L(I(c), 2);
		Kr(p), O(c);
		var m = L(c, 2), h = L(I(m), 2), g = I(h);
		Kr(g);
		var y = L(g, 2), b = I(y, !0);
		O(y), O(h), O(m);
		var w = L(m, 2), ee = I(w, !0);
		O(w), O(r), O(n);
		var te = L(n, 2), ne = I(te), re = L(I(ne), 2), ie = I(re, !0);
		O(re), O(ne);
		var ae = L(ne, 2), oe = (e) => {
			var t = pi(), n = nn(t);
			Kr(n), Fe(2), wn(() => qr(n, Y(a))), $(e, t);
		};
		Dr(ae, (e) => {
			Y(f) || e(oe);
		}), O(te);
		var se = L(te, 2), ce = I(se), le = I(ce), ue = I(le);
		O(le);
		var de = L(le, 4), fe = (e) => {
			var t = mi();
			Z("click", t, v), $(e, t);
		};
		Dr(de, (e) => {
			Y(i), X(() => Y(i).length < 10) && e(fe);
		}), O(ce);
		var pe = L(ce, 2);
		Mr(pe, 5, () => Y(i), Or, (e, t) => {
			var n = vi(), r = I(n), i = I(r), a = I(i, !0);
			O(i);
			var o = L(i, 2), s = I(o), c = (e) => {
				$(e, hi());
			}, l = (e) => {
				$(e, gi());
			};
			Dr(s, (e) => {
				Y(t), X(() => Y(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = L(s, 2), d = (e) => {
				$(e, _i());
			};
			Dr(u, (e) => {
				Y(t), X(() => Y(t).is_active) && e(d);
			}), O(o), O(r);
			var f = L(r, 2), p = I(f), m = I(p, !0);
			O(p);
			var h = L(p, 2);
			let g;
			var _ = I(h, !0);
			O(h);
			var v = L(h, 2);
			O(f), O(n), wn(() => {
				_r(a, (Y(t), X(() => Y(t).display_name || Y(t).account_name))), _r(m, (Y(t), X(() => Y(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), g = Vr(h, 1, "btn-toggle svelte-1ghyjz5", null, g, { active: Y(t).is_active }), Jr(h, "title", (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate"))), _r(_, (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate")));
			}), Z("click", p, () => C(Y(t).id)), Z("click", h, () => S(Y(t).id, Y(t).is_active)), Z("click", v, () => x(Y(t).id, Y(t).display_name || Y(t).account_name)), $(e, n);
		}, (e) => {
			$(e, yi());
		}), O(pe), O(se), wn(() => {
			Jr(g, "type", Y(u) ? "text" : "password"), Jr(g, "placeholder", Y(l) ? "••••••••  (leave blank to keep current)" : "Enter your MusicBrainz Client Secret"), Jr(y, "title", Y(u) ? "Hide" : "Show"), _r(b, Y(u) ? "👁️" : "👁️‍🗨️"), w.disabled = Y(d), _r(ee, Y(d) ? "Saving…" : "Save Credentials"), _r(ie, Y(f) ? "Expand" : "Collapse"), _r(ue, `Accounts (${(Y(i), X(() => Y(i).length)) ?? ""}/10)`);
		}), Qr(p, () => Y(o), (e) => P(o, e)), Qr(g, () => Y(s), (e) => P(s, e)), Z("click", y, () => P(u, !Y(u))), Z("click", w, _), Z("click", re, () => P(f, !Y(f))), $(e, t);
	};
	Dr(ne, (e) => {
		Y(r) ? e(re) : e(ie, -1);
	}), O(te);
	var ae = L(te, 2), oe = (e) => {
		var n = xi(), r = I(n), i = I(r), a = L(I(i), 2);
		O(i);
		var o = L(i, 2), s = I(o), c = L(I(s), 2);
		Kr(c), O(s), Fe(2), O(o);
		var l = L(o, 2), u = I(l), d = L(u, 2), f = I(d, !0);
		O(d), O(l), O(r), O(n), wn(() => {
			d.disabled = Y(h), _r(f, Y(h) ? "Adding…" : "Add Account");
		}), Z("click", a, y), Qr(c, () => Y(m), (e) => P(m, e)), Z("click", u, y), Z("click", d, b), Z("click", r, ti(function(e) {
			ii.call(this, t, e);
		})), Z("click", n, y), $(e, n);
	};
	return Dr(ae, (e) => {
		Y(p) && e(oe);
	}), $(e, ee), Ue(w);
}
customElements.define("musicbrainz-dashboard-card", di(wi, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { wi as default };

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
	return D(/* @__PURE__ */ nn(E));
}
function O(e) {
	if (T) {
		if (/* @__PURE__ */ nn(E) !== null) throw je(), r;
		E = e;
	}
}
function Fe(e = 1) {
	if (T) {
		for (var t = e, n = E; t--;) n = /* @__PURE__ */ nn(n);
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
		var i = /* @__PURE__ */ nn(n);
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
		for (var r of n) vn(r);
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
				o ? i.f ^= S : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : Yn(i) && (a & 16 && this.#l.add(i), er(i));
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
			if (!(r.f & 24576) && Yn(r) && (gt = /* @__PURE__ */ new Set(), er(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && jn(r), gt?.size > 0)) {
				Bt.clear();
				for (let e of gt) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) gt.has(n) && (gt.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || er(n);
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
		hn() && (Y(n), wn(() => (t === 0 && (r = X(() => e(() => qt(n)))), t += 1, () => {
			qe(() => {
				--t, t === 0 && (r?.(), r = void 0, qt(n));
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
		}, this.parent = W.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = En(() => {
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
			e.append(t), this.#a = this.#x(() => z(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, Mn(this.#o, () => {
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
				In(this.#a, e);
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
		Vn(this.#i), U(this.#i), Ve(this.#i.ctx);
		try {
			return pt.ensure(), e();
		} catch (e) {
			return Ye(e), null;
		} finally {
			Vn(t), U(n), Ve(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && Mn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, qe(() => {
			this.#d = !1, this.#m && Gt(this.#m, this.#l);
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
			r = !0, i && ke(), this.#s !== null && Mn(this.#s, () => {
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
		Vn(e), U(t), Ve(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function kt(e = !0) {
	Vn(null), U(null), Ve(null), e && j?.deactivate();
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
	return Cn(() => {
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
				if (i.activate(), n) o.f |= de, Gt(o, n);
				else {
					o.f & 8388608 && (o.f ^= de), Gt(o, e);
					for (let [e, t] of c) {
						if (c.delete(e), e === i) break;
						t.reject(he);
					}
				}
				i.deactivate();
			}
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), gn(() => {
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
	if (!zn && r !== null && r.f & 24576) return Ae(), e.v;
	Vn(r);
	try {
		e.f &= ~ce, Pt(e), t = Zn(e);
	} finally {
		Vn(n);
	}
	return t;
}
function It(e) {
	var t = Ft(e);
	if (!e.equals(t) && (e.wv = Jn(), (!j?.is_fork || e.deps === null) && (j === null ? e.v = t : j.capture(e, t, !0), e.deps === null))) {
		A(e, S);
		return;
	}
	zn || (M === null ? Qe(e) : (hn() || j?.is_fork) && M.set(e, t));
}
function Lt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(he), t.teardown = v, t.ac = null, $n(t, 0), On(t));
}
function Rt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && er(t);
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
	return Hn(n), n;
}
/* @__NO_SIDE_EFFECTS__ */
function N(e, n = !1, r = !0) {
	let i = Ht(e);
	return n || (i.equals = Be), t && r && k !== null && k.l !== null && (k.l.s ??= []).push(i), i;
}
function Wt(e, t) {
	return P(e, X(() => Y(e))), t;
}
function P(e, t, n = !1) {
	return V !== null && (!H || V.f & 131072) && We() && V.f & 4325394 && (G === null || !c.call(G, e)) && Oe(), Gt(e, n ? Yt(t) : t, ut);
}
function Gt(e, t, n = null) {
	if (!e.equals(t)) {
		Bt.set(e, zn ? t : e.v);
		var r = pt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Ft(t), M === null && Qe(t);
		}
		e.wv = Jn(), Jt(e, C, n), We() && W !== null && W.f & 1024 && !(W.f & 96) && (J === null ? Un([e]) : J.push(e)), !r.is_fork && zt.size > 0 && !Vt && Kt();
	}
	return t;
}
function Kt() {
	Vt = !1;
	for (let e of zt) e.f & 1024 && A(e, w), Yn(e) && er(e);
	zt.clear();
}
function qt(e) {
	P(e, e.v + 1);
}
function Jt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = We(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === W)) {
			var l = (c & C) === 0;
			if (l && A(s, t), c & 2) {
				var u = s;
				M?.delete(u), c & 65536 || (c & 512 && (s.f |= ce), Jt(u, w, n));
			} else if (l) {
				var d = s;
				c & 16 && gt !== null && gt.add(d), n === null ? bt(d) : n.push(d);
			}
		}
	}
}
function Yt(e) {
	if (typeof e != "object" || !e || fe in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ Ut(0), s = null, c = Kn, l = (e) => {
		if (Kn === c) return e();
		var t = V, n = Kn;
		U(null), qn(c);
		var r = e();
		return U(t), qn(n), r;
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
					n.set(t, e), qt(a);
				}
			} else P(r, i), qt(a);
			return !0;
		},
		get(t, r, a) {
			if (r === fe) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ Ut(Yt(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
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
			return (r !== void 0 || W !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ Ut(a ? Yt(e[t]) : i, s)), n.set(t, r)), Y(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Ut(i, s)), n.set(p + "", m)) : P(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Ut(void 0, s)), P(u, Yt(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => Yt(o));
				P(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && P(_, v + 1);
				}
				qt(a);
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
var Xt, Zt, Qt, $t;
function en() {
	if (Xt === void 0) {
		Xt = window, Zt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Qt = f(t, "firstChild").get, $t = f(t, "nextSibling").get, _(e) && (e.__click = void 0, e.__className = void 0, e.__attributes = null, e.__style = void 0, e.__e = void 0), _(n) && (n.__t = void 0);
	}
}
function F(e = "") {
	return document.createTextNode(e);
}
/* @__NO_SIDE_EFFECTS__ */
function tn(e) {
	return Qt.call(e);
}
/* @__NO_SIDE_EFFECTS__ */
function nn(e) {
	return $t.call(e);
}
function I(e, t) {
	if (!T) return /* @__PURE__ */ tn(e);
	var n = /* @__PURE__ */ tn(E);
	if (n === null) n = E.appendChild(F());
	else if (t && n.nodeType !== 3) {
		var r = F();
		return n?.before(r), D(r), r;
	}
	return t && cn(n), D(n), n;
}
function rn(e, t = !1) {
	if (!T) {
		var n = /* @__PURE__ */ tn(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ nn(n) : n;
	}
	if (t) {
		if (E?.nodeType !== 3) {
			var r = F();
			return E?.before(r), D(r), r;
		}
		cn(E);
	}
	return E;
}
function L(e, t = 1, n = !1) {
	let r = T ? E : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ nn(r);
	if (!T) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = F();
			return r === null ? i?.after(a) : r.before(a), D(a), a;
		}
		cn(r);
	}
	return D(r), r;
}
function an(e) {
	e.textContent = "";
}
function on() {
	return !e || gt !== null ? !1 : (W.f & ne) !== 0;
}
function sn(e, t, n) {
	let r = n ? { is: n } : void 0;
	return document.createElementNS(t ?? "http://www.w3.org/1999/xhtml", e, r);
}
function cn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var ln = !1;
function un() {
	ln || (ln = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t.__on_r?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function dn(e) {
	var t = V, n = W;
	U(null), Vn(null);
	try {
		return e();
	} finally {
		U(t), Vn(n);
	}
}
function fn(e, t, n, r = n) {
	e.addEventListener(t, () => dn(n));
	let i = e.__on_r;
	i ? e.__on_r = () => {
		i(), r(!0);
	} : e.__on_r = () => r(!0), un();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function pn(e) {
	W === null && (V === null && Se(e), xe()), zn && be(e);
}
function mn(e, t) {
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
			er(r);
		} catch (e) {
			throw B(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= ie));
	}
	if (i !== null && (i.parent = n, n !== null && mn(i, n), V !== null && V.f & 2 && !(e & 64))) {
		var a = V;
		(a.effects ??= []).push(i);
	}
	return r;
}
function hn() {
	return V !== null && !H;
}
function gn(e) {
	let t = R(8, null);
	return A(t, S), t.teardown = e, t;
}
function _n(e) {
	pn("$effect");
	var t = W.f;
	if (!V && t & 32 && !(t & 32768)) {
		var n = k;
		(n.e ??= []).push(e);
	} else return vn(e);
}
function vn(e) {
	return R(4 | oe, e);
}
function yn(e) {
	return pn("$effect.pre"), R(8 | oe, e);
}
function bn(e) {
	pt.ensure();
	let t = R(64 | ae, e);
	return () => {
		B(t);
	};
}
function xn(e) {
	pt.ensure();
	let t = R(64 | ae, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Mn(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function Sn(e) {
	return R(4, e);
}
function Cn(e) {
	return R(ue | ae, e);
}
function wn(e, t = 0) {
	return R(8 | t, e);
}
function Tn(e, t = [], n = [], r = []) {
	Dt(r, t, n, (t) => {
		R(8, () => e(...t.map(Y)));
	});
}
function En(e, t = 0) {
	return R(16 | t, e);
}
function z(e) {
	return R(32 | ae, e);
}
function Dn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = zn, n = V;
		Bn(!0), U(null);
		try {
			t.call(null);
		} finally {
			Bn(e), U(n);
		}
	}
}
function On(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && dn(() => {
			e.abort(he);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function kn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (An(e.nodes.start, e.nodes.end), n = !0), A(e, re), On(e, t && !n), $n(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Dn(e), e.f ^= re, e.f |= te;
	var i = e.parent;
	i !== null && i.first !== null && jn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function An(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ nn(e);
		e.remove(), e = n;
	}
}
function jn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Mn(e, t, n = !0) {
	var r = [];
	Nn(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function Nn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ee;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				Nn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Pn(e) {
	Fn(e, !0);
}
function Fn(e, t) {
	if (e.f & 8192) {
		e.f ^= ee, e.f & 1024 || (A(e, C), pt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Fn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function In(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ nn(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Ln = null, Rn = !1, zn = !1;
function Bn(e) {
	zn = e;
}
var V = null, H = !1;
function U(e) {
	V = e;
}
var W = null;
function Vn(e) {
	W = e;
}
var G = null;
function Hn(t) {
	V !== null && (!e || V.f & 2) && (G === null ? G = [t] : G.push(t));
}
var K = null, q = 0, J = null;
function Un(e) {
	J = e;
}
var Wn = 1, Gn = 0, Kn = Gn;
function qn(e) {
	Kn = e;
}
function Jn() {
	return ++Wn;
}
function Yn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~ce), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Yn(a) && It(a), a.wv > e.wv) return !0;
		}
		t & 512 && M === null && A(e, S);
	}
	return !1;
}
function Xn(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && G !== null && c.call(G, t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? Xn(o, n, !1) : n === o && (r ? A(o, C) : o.f & 1024 && A(o, w), bt(o));
	}
}
function Zn(e) {
	var t = K, n = q, r = J, i = V, a = G, o = k, s = H, c = Kn, l = e.f;
	K = null, q = 0, J = null, V = l & 96 ? null : e, G = null, Ve(e.ctx), H = !1, Kn = ++Gn, e.ac !== null && (dn(() => {
		e.ac.abort(he);
	}), e.ac = null);
	try {
		e.f |= le;
		var u = e.fn, d = u();
		e.f |= ne;
		var f = e.deps, p = j?.is_fork;
		if (K !== null) {
			var m;
			if (p || $n(e, q), f !== null && q > 0) for (f.length = q + K.length, m = 0; m < K.length; m++) f[q + m] = K[m];
			else e.deps = f = K;
			if (hn() && e.f & 512) for (m = q; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && q < f.length && ($n(e, q), f.length = q);
		if (We() && J !== null && !H && f !== null && !(e.f & 6146)) for (m = 0; m < J.length; m++) Xn(J[m], e);
		if (i !== null && i !== e) {
			if (Gn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Gn;
			if (t !== null) for (let e of t) e.rv = Gn;
			J !== null && (r === null ? r = J : r.push(...J));
		}
		return e.f & 8388608 && (e.f ^= de), d;
	} catch (e) {
		return Ye(e);
	} finally {
		e.f ^= le, K = t, q = n, J = r, V = i, G = a, Ve(o), H = s, Kn = c;
	}
}
function Qn(e, t) {
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
		o.f & 512 && (o.f ^= 512, o.f &= ~ce), o.v !== i && Qe(o), Lt(o), $n(o, 0);
	}
}
function $n(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Qn(e, n[r]);
}
function er(e) {
	var t = e.f;
	if (!(t & 16384)) {
		A(e, S);
		var n = W, r = Rn;
		W = e, Rn = !0;
		try {
			t & 16777232 ? kn(e) : On(e), Dn(e);
			var i = Zn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Wn;
		} finally {
			Rn = r, W = n;
		}
	}
}
async function tr() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), mt();
}
function Y(e) {
	var t = (e.f & 2) != 0;
	if (Ln?.add(e), V !== null && !H && !(W !== null && W.f & 16384) && (G === null || !c.call(G, e))) {
		var n = V.deps;
		if (V.f & 2097152) e.rv < Gn && (e.rv = Gn, K === null && n !== null && n[q] === e ? q++ : K === null ? K = [e] : K.push(e));
		else {
			(V.deps ??= []).push(e);
			var r = e.reactions;
			r === null ? e.reactions = [V] : c.call(r, V) || r.push(V);
		}
	}
	if (zn && Bt.has(e)) return Bt.get(e);
	if (t) {
		var i = e;
		if (zn) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || rr(i)) && (a = Ft(i)), Bt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !H && V !== null && (Rn || (V.f & 512) != 0), s = (i.f & ne) === 0;
		Yn(i) && (o && (i.f |= 512), It(i)), o && !s && (Rt(i), nr(i));
	}
	if (M?.has(e)) return M.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function nr(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Rt(t), nr(t));
}
function rr(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Bt.has(t) || t.f & 2 && rr(t)) return !0;
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
function ir(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (fe in e) ar(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && fe in n && ar(n);
		}
	}
}
function ar(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			ar(e[n], t);
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
var or = Symbol("events"), sr = /* @__PURE__ */ new Set(), cr = /* @__PURE__ */ new Set();
function lr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || dr.call(t, e), !e.cancelBubble) return dn(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? qe(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function Z(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = lr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && gn(() => {
		t.removeEventListener(e, o, a);
	});
}
var ur = null;
function dr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	ur = e;
	var o = 0, s = ur === e && e[or];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[or] = t;
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
		U(null), Vn(null);
		try {
			for (var p, m = []; a !== null;) {
				var h = a.assignedSlot || a.parentNode || a.host || null;
				try {
					var g = a[or]?.[r];
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
			e[or] = t, delete e.currentTarget, U(u), Vn(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var fr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function pr(e) {
	return fr?.createHTML(e) ?? e;
}
function mr(e) {
	var t = sn("template");
	return t.innerHTML = pr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function hr(e, t) {
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
		if (T) return hr(E, null), E;
		i === void 0 && (i = mr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ tn(i)));
		var t = r || Zt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ tn(t), s = t.lastChild;
			hr(o, s);
		} else hr(t, t);
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
var gr = ["touchstart", "touchmove"];
function _r(e) {
	return gr.includes(e);
}
function vr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e.__t ??= e.nodeValue) && (e.__t = n, e.nodeValue = `${n}`);
}
function yr(e, t) {
	return Sr(e, t);
}
function br(e, t) {
	en(), t.intro = t.intro ?? !1;
	let n = t.target, i = T, a = E;
	try {
		for (var o = /* @__PURE__ */ tn(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ nn(o);
		if (!o) throw r;
		Ne(!0), D(o);
		let i = Sr(e, {
			...t,
			anchor: o
		});
		return Ne(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && we(), en(), an(n), Ne(!1), yr(e, t);
	} finally {
		Ne(i), D(a);
	}
}
var xr = /* @__PURE__ */ new Map();
function Sr(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	en();
	var u = void 0, d = xn(() => {
		var s = n ?? t.appendChild(F());
		Tt(s, { pending: () => {} }, (t) => {
			He({});
			var n = k;
			if (o && (n.c = o), a && (i.$$events = a), T && hr(t, null), u = e(t, i) || {}, T && (W.nodes.end = E, E === null || E.nodeType !== 8 || E.data !== "]")) throw je(), r;
			Ue();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = _r(r);
					for (let e of [t, document]) {
						var a = xr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), xr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, dr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(sr)), cr.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = xr.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, dr), r.delete(e), r.size === 0 && xr.delete(n)) : r.set(e, i);
			}
			cr.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return Cr.set(u, d), u;
}
var Cr = /* @__PURE__ */ new WeakMap();
function wr(e, t) {
	let n = Cr.get(e);
	return n ? (Cr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
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
			if (n) Pn(n), this.#r.delete(t);
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
						In(r, t), t.append(F()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Mn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = j, r = on();
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
function Er(e) {
	k === null && _e("onMount"), t && k.l !== null ? Dr(k).m.push(e) : _n(() => {
		let t = X(e);
		if (typeof t == "function") return t;
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
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Or(e, t, n = !1) {
	var r;
	T && (r = E, Pe());
	var i = new Tr(e), a = n ? ie : 0;
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
	En(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/each.js
function kr(e, t) {
	return t;
}
function Ar(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		Mn(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					jr(e, l(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var c = r.length === 0 && n !== null;
		if (c) {
			var u = n, d = u.parentNode;
			an(d), d.append(u), e.items.clear();
		}
		jr(e, t, !c);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function jr(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= se, In(a, document.createDocumentFragment())) : B(t[i], n);
	}
}
var Mr;
function Nr(e, t, n, r, i, a = null) {
	var s = e, c = /* @__PURE__ */ new Map();
	if (t & 4) {
		var u = e;
		s = T ? D(/* @__PURE__ */ tn(u)) : u.appendChild(F());
	}
	T && Pe();
	var d = null, f = /* @__PURE__ */ Nt(() => {
		var e = n();
		return o(e) ? e : e == null ? [] : l(e);
	}), p, m = /* @__PURE__ */ new Map(), h = !0;
	function g(e) {
		v.effect.f & 16384 || (v.pending.delete(e), v.fallback = d, Fr(v, p, s, t, r), d !== null && (p.length === 0 ? d.f & 33554432 ? (d.f ^= se, Lr(d, null, s)) : Pn(d) : Mn(d, () => {
			d = null;
		})));
	}
	function _(e) {
		v.pending.delete(e);
	}
	var v = {
		effect: En(() => {
			p = Y(f);
			var e = p.length;
			let o = !1;
			T && Le(s) === "[!" != (e === 0) && (s = Ie(), D(s), Ne(!1), o = !0);
			for (var l = /* @__PURE__ */ new Set(), u = j, v = on(), y = 0; y < e; y += 1) {
				T && E.nodeType === 8 && E.data === "]" && (s = E, o = !0, Ne(!1));
				var b = p[y], x = r(b, y), S = h ? null : c.get(x);
				S ? (S.v && Gt(S.v, b), S.i && Gt(S.i, y), v && u.unskip_effect(S.e)) : (S = Ir(c, h ? s : Mr ??= F(), b, x, y, i, t, n), h || (S.e.f |= se), c.set(x, S)), l.add(x);
			}
			if (e === 0 && a && !d && (h ? d = z(() => a(s)) : (d = z(() => a(Mr ??= F())), d.f |= se)), e > l.size && ye("", "", ""), T && e > 0 && D(Ie()), !h) if (m.set(u, l), v) {
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
function Pr(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function Fr(e, t, n, r, i) {
	var a = (r & 8) != 0, o = t.length, s = e.items, c = Pr(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (Pn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) if (_.f ^= se, _ === c) Lr(_, null, n);
		else {
			var y = d ? d.next : c;
			_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), Rr(e, d, _), Rr(e, _, y), Lr(_, y, n), d = _, p = [], m = [], c = Pr(d.next);
			continue;
		}
		if (_ !== c) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) Lr(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					Rr(e, S.prev, C.next), Rr(e, d, S), Rr(e, C, b), c = b, d = C, --v, p = [], m = [];
				} else u.delete(_), Lr(_, c, n), Rr(e, _.prev, _.next), Rr(e, _, d === null ? e.effect.first : d.next), Rr(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; c !== null && c !== _;) (u ??= /* @__PURE__ */ new Set()).add(c), m.push(c), c = Pr(c.next);
			if (c === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, c = Pr(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (jr(e, l(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (c !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; c !== null;) !(c.f & 8192) && c !== e.fallback && w.push(c), c = Pr(c.next);
		var ee = w.length;
		if (ee > 0) {
			var te = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.fix();
			}
			Ar(e, w, te);
		}
	}
	a && qe(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function Ir(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Ht(n) : /* @__PURE__ */ N(n, !1, !1) : null, l = o & 2 ? Ht(i) : null;
	return {
		v: c,
		i: l,
		e: z(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function Lr(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ nn(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function Rr(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function zr(e, t) {
	Sn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = sn("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/shared/attributes.js
var Br = [..." 	\n\r\f\xA0\v﻿"];
function Vr(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Br.includes(r[o - 1])) && (s === r.length || Br.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/class.js
function Hr(e, t, n, r, i, a) {
	var o = e.__className;
	if (T || o !== n || o === void 0) {
		var s = Vr(n, r, a);
		(!T || s !== e.getAttribute("class")) && (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e.__className = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Ur = Symbol("is custom element"), Wr = Symbol("is html"), Gr = ge ? "link" : "LINK";
function Kr(e) {
	if (T) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					qr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					qr(e, "checked", null), e.checked = r;
				}
			}
		};
		e.__on_r = n, qe(n), un();
	}
}
function qr(e, t, n, r) {
	var i = Jr(e);
	T && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Gr) || i[t] !== (i[t] = n) && (t === "loading" && (e[me] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Xr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function Jr(e) {
	return e.__attributes ??= {
		[Ur]: e.nodeName.includes("-"),
		[Wr]: e.namespaceURI === a
	};
}
var Yr = /* @__PURE__ */ new Map();
function Xr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Yr.get(t);
	if (n) return n;
	Yr.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Zr(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	fn(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = Qr(t) ? $r(a) : a, r(a), j !== null && i.add(j), await tr(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (T && t.defaultValue !== t.value || X(n) == null && t.value) && (r(Qr(t) ? $r(t.value) : t.value), j !== null && i.add(j)), wn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? at : j;
			if (i.has(a)) return;
		}
		Qr(t) && r === $r(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function Qr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function $r(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function ei(e) {
	return function(...t) {
		return t[0].stopPropagation(), e?.apply(this, t);
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function ti(e = !1) {
	let t = k, n = t.l.u;
	if (!n) return;
	let r = () => ir(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ jt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Y(i);
	}
	n.b.length && yn(() => {
		ni(t, r), b(n.b);
	}), _n(() => {
		let e = X(() => n.m.map(y));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && _n(() => {
		ni(t, r), b(n.a);
	});
}
function ni(e, t) {
	if (e.l.s) for (let t of e.l.s) Y(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/misc.js
function ri(e, t) {
	var n = e.$$events?.[t.type];
	for (var r of o(n) ? n.slice() : n == null ? [] : [n]) r.call(this, t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function ii(e, n, r, i) {
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
			let n = t ? Y(y) : a && o ? Yt(e) : e;
			return P(y, n), v = !0, c !== void 0 && (c = n), e;
		}
		return zn && v || b.f & 16384 ? y.v : Y(y);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function ai(e) {
	return new oi(e);
}
var oi = class {
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
		this.#t = (t.hydrate ? br : yr)(t.component, {
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
}, si;
typeof HTMLElement == "function" && (si = class extends HTMLElement {
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
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = li(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = ci(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = ai({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = bn(() => {
				wn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = ci(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = ci(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
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
function ci(e, t, n, r) {
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
function li(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function ui(e, t, n, r, i, a) {
	let o = class extends si {
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
				n = ci(e, n, t), this.$$d[e] = n;
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
//#region TidalCard.svelte
var di = /* @__PURE__ */ Q("<div class=\"loading svelte-11pw7by\">Loading...</div>"), fi = /* @__PURE__ */ Q("<div class=\"redirect-uri-group svelte-11pw7by\"><input type=\"text\" placeholder=\"Loading dynamic redirect URI...\" class=\"input readonly-input svelte-11pw7by\"/></div> <p class=\"help-text svelte-11pw7by\" style=\"margin-top: 8px;\">This auto-generated URI must be registered in all of your Tidal Developer Applications.</p>", 1), pi = /* @__PURE__ */ Q("<button class=\"btn-secondary svelte-11pw7by\">+ Add Account</button>"), mi = /* @__PURE__ */ Q("<span class=\"status-badge authenticated svelte-11pw7by\">✓ Authenticated</span>"), hi = /* @__PURE__ */ Q("<span class=\"status-badge unauthenticated svelte-11pw7by\">⚠ Not Authenticated</span>"), gi = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-11pw7by\">● Active</span>"), _i = /* @__PURE__ */ Q("<span class=\"status-badge configured svelte-11pw7by\">🔒 Configured</span>"), vi = /* @__PURE__ */ Q("<div class=\"account-row svelte-11pw7by\"><div class=\"account-info svelte-11pw7by\"><div class=\"account-name svelte-11pw7by\"> </div> <div class=\"account-status svelte-11pw7by\"><!> <!> <!></div></div> <div class=\"account-actions svelte-11pw7by\"><button class=\"btn-link svelte-11pw7by\" title=\"Edit credentials\">⚙️ Edit</button> <button class=\"btn-link svelte-11pw7by\"> </button> <button> </button> <button class=\"btn-delete svelte-11pw7by\">✕</button></div></div>"), yi = /* @__PURE__ */ Q("<div class=\"empty-state svelte-11pw7by\">No accounts added yet. Click \"Add Account\" to get started.</div>"), bi = /* @__PURE__ */ Q("<div class=\"section svelte-11pw7by\"><div class=\"section-header svelte-11pw7by\"><h3 class=\"svelte-11pw7by\">Global Redirect URI (Auto-generated & Immutable)</h3> <button class=\"btn-secondary svelte-11pw7by\"> </button></div> <!></div> <div class=\"section svelte-11pw7by\"><div class=\"section-header svelte-11pw7by\"><h3 class=\"svelte-11pw7by\"> </h3> <p class=\"help-text svelte-11pw7by\">Tidal requires per-account Client ID and Secret.</p> <!></div> <div class=\"accounts-list svelte-11pw7by\"></div></div>", 1), xi = /* @__PURE__ */ Q("<div class=\"modal-overlay svelte-11pw7by\"><div class=\"modal-content svelte-11pw7by\"><div class=\"modal-header svelte-11pw7by\"><h3 class=\"svelte-11pw7by\"> </h3> <button class=\"modal-close svelte-11pw7by\">✕</button></div> <div class=\"modal-body svelte-11pw7by\"><label class=\"svelte-11pw7by\"><span class=\"label-text svelte-11pw7by\">Account Name</span> <input type=\"text\" placeholder=\"My Tidal Account\" class=\"input svelte-11pw7by\"/></label> <label class=\"svelte-11pw7by\"><span class=\"label-text svelte-11pw7by\">Client ID</span> <input type=\"text\" placeholder=\"Enter Tidal Client ID\" class=\"input svelte-11pw7by\"/></label> <label class=\"svelte-11pw7by\"><span class=\"label-text svelte-11pw7by\">Client Secret</span> <div class=\"password-field svelte-11pw7by\"><input placeholder=\"Enter Tidal Client Secret\" class=\"input svelte-11pw7by\"/> <button type=\"button\" class=\"password-toggle svelte-11pw7by\"> </button></div></label> <p class=\"modal-help svelte-11pw7by\">Each Tidal account requires its own Client ID and Client Secret from the Tidal Developer Portal.</p></div> <div class=\"modal-footer svelte-11pw7by\"><button class=\"btn-secondary svelte-11pw7by\">Cancel</button> <button class=\"btn-primary svelte-11pw7by\"> </button></div></div></div>"), Si = /* @__PURE__ */ Q("<section class=\"tidal-card card svelte-11pw7by\"><div class=\"card-header svelte-11pw7by\"><div class=\"header-left svelte-11pw7by\"><h2 class=\"svelte-11pw7by\">Tidal</h2> <span class=\"provider-badge svelte-11pw7by\">Streaming Service</span></div></div> <!></section> <!>", 1), Ci = {
	hash: "svelte-11pw7by",
	code: ".tidal-card.svelte-11pw7by {padding:20px;margin-bottom:16px;}.card-header.svelte-11pw7by {display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid var(--border-color, rgba(255,255,255,0.1));}.header-left.svelte-11pw7by {display:flex;align-items:center;gap:12px;}.card-header.svelte-11pw7by h2:where(.svelte-11pw7by) {margin:0;font-size:20px;font-weight:600;}.provider-badge.svelte-11pw7by {font-size:12px;padding:4px 8px;border-radius:4px;background:rgba(0, 180, 255, 0.2);color:#00b4ff;}.section.svelte-11pw7by {margin-bottom:24px;}.section.svelte-11pw7by h3:where(.svelte-11pw7by) {margin:0 0 8px 0;font-size:16px;font-weight:600;}.help-text.svelte-11pw7by {font-size:13px;color:var(--muted);margin:0 0 12px 0;}.section-header.svelte-11pw7by {margin-bottom:12px;}.section-header.svelte-11pw7by h3:where(.svelte-11pw7by) {margin-bottom:4px;}.section-header.svelte-11pw7by button:where(.svelte-11pw7by) {margin-top:8px;}.redirect-uri-group.svelte-11pw7by {display:flex;gap:8px;}.redirect-uri-group.svelte-11pw7by .input:where(.svelte-11pw7by) {flex:1;}.input.svelte-11pw7by {padding:8px 12px;border-radius:6px;background:var(--input-bg, rgba(255,255,255,0.05));border:1px solid var(--border-color, rgba(255,255,255,0.1));color:var(--text);font-size:14px;width:100%;}.input.svelte-11pw7by:focus {outline:none;border-color:#00b4ff;}.readonly-input.svelte-11pw7by {opacity:0.7;cursor:not-allowed;background:rgba(0, 0, 0, 0.2);user-select:all;}.btn-primary.svelte-11pw7by, .btn-secondary.svelte-11pw7by, .btn-link.svelte-11pw7by, .btn-toggle.svelte-11pw7by, .btn-delete.svelte-11pw7by {padding:8px 16px;border-radius:6px;border:none;cursor:pointer;font-size:14px;transition:all 0.2s;}.btn-primary.svelte-11pw7by {background:#00b4ff;color:white;}.btn-primary.svelte-11pw7by:hover:not(:disabled) {background:#0099dd;}.btn-primary.svelte-11pw7by:disabled {opacity:0.5;cursor:not-allowed;}.btn-secondary.svelte-11pw7by {background:rgba(255,255,255,0.1);color:var(--text);}.btn-secondary.svelte-11pw7by:hover {background:rgba(255,255,255,0.15);}.btn-link.svelte-11pw7by {background:transparent;color:#00b4ff;padding:4px 8px;}.btn-link.svelte-11pw7by:hover {text-decoration:underline;}.btn-toggle.svelte-11pw7by {background:rgba(255,255,255,0.1);color:var(--text);}.btn-toggle.active.svelte-11pw7by {background:rgba(0, 180, 255, 0.2);color:#00b4ff;}.btn-toggle.svelte-11pw7by:hover {background:rgba(255,255,255,0.15);}.btn-delete.svelte-11pw7by {background:rgba(239, 68, 68, 0.2);color:#ef4444;padding:6px 10px;}.btn-delete.svelte-11pw7by:hover {background:rgba(239, 68, 68, 0.3);}.accounts-list.svelte-11pw7by {display:flex;flex-direction:column;gap:8px;}.account-row.svelte-11pw7by {display:flex;justify-content:space-between;align-items:center;padding:12px;background:rgba(255,255,255,0.05);border-radius:6px;border:1px solid var(--border-color, rgba(255,255,255,0.1));}.account-info.svelte-11pw7by {display:flex;flex-direction:column;gap:6px;}.account-name.svelte-11pw7by {font-weight:500;font-size:14px;}.account-status.svelte-11pw7by {display:flex;gap:8px;flex-wrap:wrap;}.status-badge.svelte-11pw7by {font-size:12px;padding:2px 8px;border-radius:4px;}.status-badge.authenticated.svelte-11pw7by {background:rgba(34, 197, 94, 0.2);color:#22c55e;}.status-badge.unauthenticated.svelte-11pw7by {background:rgba(251, 191, 36, 0.2);color:#fbbf24;}.status-badge.active.svelte-11pw7by {background:rgba(59, 130, 246, 0.2);color:#3b82f6;}.status-badge.configured.svelte-11pw7by {background:rgba(168, 85, 247, 0.2);color:#a855f7;}.account-actions.svelte-11pw7by {display:flex;gap:8px;align-items:center;}.empty-state.svelte-11pw7by {padding:24px;text-align:center;color:var(--muted);}.loading.svelte-11pw7by {padding:24px;text-align:center;color:var(--muted);}\n\n  /* Modal Styles */.modal-overlay.svelte-11pw7by {position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0, 0, 0, 0.7);display:flex;align-items:center;justify-content:center;z-index:1000;}.modal-content.svelte-11pw7by {background:var(--card-bg, #1e1e1e);border-radius:8px;width:90%;max-width:500px;max-height:90vh;overflow-y:auto;box-shadow:0 4px 24px rgba(0, 0, 0, 0.5);}.modal-header.svelte-11pw7by {display:flex;justify-content:space-between;align-items:center;padding:20px;border-bottom:1px solid var(--border-color, rgba(255,255,255,0.1));}.modal-header.svelte-11pw7by h3:where(.svelte-11pw7by) {margin:0;font-size:18px;font-weight:600;}.modal-close.svelte-11pw7by {background:transparent;border:none;color:var(--text);font-size:20px;cursor:pointer;padding:4px 8px;}.modal-close.svelte-11pw7by:hover {color:#ef4444;}.modal-body.svelte-11pw7by {padding:20px;}.modal-body.svelte-11pw7by label:where(.svelte-11pw7by) {display:flex;flex-direction:column;gap:6px;margin-bottom:16px;}.label-text.svelte-11pw7by {font-size:14px;color:var(--text);font-weight:500;}.modal-help.svelte-11pw7by {font-size:13px;color:var(--muted);margin-top:8px;}.password-field.svelte-11pw7by {position:relative;display:flex;align-items:center;}.password-field.svelte-11pw7by .input:where(.svelte-11pw7by) {flex:1;padding-right:40px;}.password-toggle.svelte-11pw7by {position:absolute;right:8px;background:transparent;border:none;color:var(--text);cursor:pointer;font-size:18px;padding:4px 8px;opacity:0.6;transition:opacity 0.2s;}.password-toggle.svelte-11pw7by:hover {opacity:1;}.modal-footer.svelte-11pw7by {display:flex;justify-content:flex-end;gap:8px;padding:16px 20px;border-top:1px solid var(--border-color, rgba(255,255,255,0.1));}"
};
function wi(e, t) {
	He(t, !1), zr(e, Ci);
	let n = ii(t, "apiBase", 12, ""), r = /* @__PURE__ */ N([]), i = /* @__PURE__ */ N(""), a = /* @__PURE__ */ N(!1), o = /* @__PURE__ */ N(!0), s = /* @__PURE__ */ N(!1), c = /* @__PURE__ */ N("add"), l = /* @__PURE__ */ N({
		id: null,
		account_name: "",
		client_id: "",
		client_secret: ""
	}), u = /* @__PURE__ */ N(!1), d = /* @__PURE__ */ N(!1);
	Er(async () => {
		await f(), P(a, !!Y(i)), P(o, !1);
	});
	async function f() {
		try {
			let e = await fetch(`${n()}/accounts/tidal`);
			e.data && (P(r, e.data.accounts || []), P(i, e.data.redirect_uri || ""), P(a, !!Y(i)));
		} catch (e) {
			console.error("Failed to load Tidal accounts:", e), console.error("Failed to load Tidal accounts");
		}
	}
	function p() {
		P(c, "add"), P(l, {
			id: null,
			account_name: "",
			client_id: "",
			client_secret: ""
		}), P(u, !0), P(d, !1), P(s, !0);
	}
	async function m(e) {
		P(c, "edit");
		try {
			let t = await fetch(`${n()}/accounts/tidal/${e.id}`);
			t.data?.account && (P(l, {
				id: t.data.account.id,
				account_name: t.data.account.account_name,
				client_id: t.data.account.client_id || "",
				client_secret: t.data.account.client_secret || ""
			}), P(u, !1), P(d, !1), P(s, !0));
		} catch (e) {
			console.error("Failed to load account credentials:", e), console.error("Failed to load account");
		}
	}
	function h() {
		P(s, !1), P(u, !1), P(d, !1), P(l, {
			id: null,
			account_name: "",
			client_id: "",
			client_secret: ""
		});
	}
	async function g() {
		if (!Y(l).account_name.trim() || !Y(l).client_id.trim()) {
			console.error("Account name and Client ID are required");
			return;
		}
		if (!Y(l).client_secret.trim()) {
			console.error("Client Secret is required");
			return;
		}
		if (Y(c) === "add" && Y(r).length >= 25) {
			console.error("Maximum 25 accounts allowed");
			return;
		}
		try {
			let e = {
				account_name: Y(l).account_name,
				client_id: Y(l).client_id,
				client_secret: Y(l).client_secret
			};
			Y(c) === "add" ? (await fetch(`${n()}/accounts/tidal`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), console.log("Account added")) : (await fetch(`${n()}/accounts/tidal/${Y(l).id}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), console.log("Account updated")), h(), await f();
		} catch (e) {
			console.error("Failed to save account:", e), console.error("Failed to save account");
		}
	}
	async function _(e, t) {
		try {
			await fetch(`${n()}/accounts/tidal/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			}), console.log(t ? "Account deactivated" : "Account activated"), await f();
		} catch (e) {
			console.error("Failed to toggle account:", e), console.error("Failed to update account");
		}
	}
	async function v(e, t) {
		if (confirm(`Delete account "${t}"? This will also delete its credentials.`)) try {
			await fetch(`${n()}/accounts/tidal/${e}`, { method: "DELETE" }), console.log("Account deleted"), await f();
		} catch (e) {
			console.error("Failed to delete account:", e), console.error("Failed to delete account");
		}
	}
	async function y(e) {
		try {
			let t = (await fetch(`${n()}/tidal/auth?account_id=${e}`)).data?.auth_url;
			t ? window.location.href = t : console.error("Failed to get Tidal auth URL");
		} catch (e) {
			console.error("Failed to start OAuth:", e);
			let t = e?.response?.data?.error || "Failed to start OAuth";
			console.error(t);
		}
	}
	var b = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), mt();
		}
	};
	ti();
	var x = Si(), S = rn(x), C = L(I(S), 2), w = (e) => {
		$(e, di());
	}, ee = (e) => {
		var t = bi(), n = rn(t), o = I(n), s = L(I(o), 2), c = I(s, !0);
		O(s), O(o);
		var l = L(o, 2), u = (e) => {
			var t = fi(), n = rn(t), r = I(n);
			Kr(r), r.readOnly = !0, r.disabled = !0, O(n), Fe(2), Zr(r, () => Y(i), (e) => P(i, e)), $(e, t);
		};
		Or(l, (e) => {
			Y(a) || e(u);
		}), O(n);
		var d = L(n, 2), f = I(d), h = I(f), g = I(h);
		O(h);
		var b = L(h, 4), x = (e) => {
			var t = pi();
			Z("click", t, p), $(e, t);
		};
		Or(b, (e) => {
			Y(r), X(() => Y(r).length < 25) && e(x);
		}), O(f);
		var S = L(f, 2);
		Nr(S, 5, () => Y(r), kr, (e, t) => {
			var n = vi(), r = I(n), i = I(r), a = I(i, !0);
			O(i);
			var o = L(i, 2), s = I(o), c = (e) => {
				$(e, mi());
			}, l = (e) => {
				$(e, hi());
			};
			Or(s, (e) => {
				Y(t), X(() => Y(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = L(s, 2), d = (e) => {
				$(e, gi());
			};
			Or(u, (e) => {
				Y(t), X(() => Y(t).is_active) && e(d);
			});
			var f = L(u, 2), p = (e) => {
				$(e, _i());
			};
			Or(f, (e) => {
				Y(t), X(() => Y(t).client_secret_configured) && e(p);
			}), O(o), O(r);
			var h = L(r, 2), g = I(h), b = L(g, 2), x = I(b, !0);
			O(b);
			var S = L(b, 2);
			let C;
			var w = I(S, !0);
			O(S);
			var ee = L(S, 2);
			O(h), O(n), Tn(() => {
				vr(a, (Y(t), X(() => Y(t).display_name || Y(t).account_name))), vr(x, (Y(t), X(() => Y(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), C = Hr(S, 1, "btn-toggle svelte-11pw7by", null, C, { active: Y(t).is_active }), qr(S, "title", (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate"))), vr(w, (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate")));
			}), Z("click", g, () => m(Y(t))), Z("click", b, () => y(Y(t).id)), Z("click", S, () => _(Y(t).id, Y(t).is_active)), Z("click", ee, () => v(Y(t).id, Y(t).display_name || Y(t).account_name)), $(e, n);
		}, (e) => {
			$(e, yi());
		}), O(S), O(d), Tn(() => {
			vr(c, Y(a) ? "Expand" : "Collapse"), vr(g, `Accounts (${(Y(r), X(() => Y(r).length)) ?? ""}/25)`);
		}), Z("click", s, () => P(a, !Y(a))), $(e, t);
	};
	Or(C, (e) => {
		Y(o) ? e(w) : e(ee, -1);
	}), O(S);
	var te = L(S, 2), ne = (e) => {
		var n = xi(), r = I(n), i = I(r), a = I(i), o = I(a, !0);
		O(a);
		var s = L(a, 2);
		O(i);
		var f = L(i, 2), p = I(f), m = L(I(p), 2);
		Kr(m), O(p);
		var _ = L(p, 2), v = L(I(_), 2);
		Kr(v), O(_);
		var y = L(_, 2), b = L(I(y), 2), x = I(b);
		Kr(x);
		var S = L(x, 2), C = I(S, !0);
		O(S), O(b), O(y), Fe(2), O(f);
		var w = L(f, 2), ee = I(w), te = L(ee, 2), ne = I(te, !0);
		O(te), O(w), O(r), O(n), Tn(() => {
			vr(o, Y(c) === "add" ? "Add Tidal Account" : "Edit Tidal Account"), qr(x, "type", Y(d) ? "text" : "password"), qr(S, "title", Y(d) ? "Hide" : "Show"), vr(C, Y(d) ? "👁️" : "👁️‍🗨️"), vr(ne, Y(c) === "add" ? "Add Account" : "Save Changes");
		}), Z("click", s, h), Zr(m, () => Y(l).account_name, (e) => Wt(l, Y(l).account_name = e)), Zr(v, () => Y(l).client_id, (e) => Wt(l, Y(l).client_id = e)), Zr(x, () => Y(l).client_secret, (e) => Wt(l, Y(l).client_secret = e)), Z("input", x, () => P(u, !0)), Z("click", S, () => P(d, !Y(d))), Z("click", ee, h), Z("click", te, g), Z("click", r, ei(function(e) {
			ri.call(this, t, e);
		})), Z("click", n, h), $(e, n);
	};
	return Or(te, (e) => {
		Y(s) && e(ne);
	}), $(e, x), Ue(b);
}
customElements.define("tidal-dashboard-card", ui(wi, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { wi as default };
